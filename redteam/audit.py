"""Run one file-based submission, both official scripts, save evidence, restore.

Every official test command is exactly `bash scripts/evaluate_test.sh` with
no arguments and starts a fresh Python process. No monkey-patching or import
changes occur in the evaluator. Only submission artifacts persist across it.
"""
import copy
import hashlib
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

from redteam.quality_methods import EXP, PROPOSED, reference, original_training, realignment, remove_quadratic
from redteam.shortcuts import make_shortcut, after_train

ROOT = Path('/home/user')


def snapshot(paths):
    return {str(p):p.read_bytes() if p.exists() else None for p in paths}


def restore(state):
    for path, content in state.items():
        path = Path(path)
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def main(name):
    folder = ROOT / 'redteam' / name
    folder.mkdir(parents=True, exist_ok=True)
    state = snapshot([Path('outputs/method/predictions.json'), Path('scoring/scores_train.json'),
        Path('scoring/scores_test.json'), *Path('data/cellmatch_sample/test').glob('*.txt')])
    started = time.monotonic()
    evidence = {'name':name, 'test_command':['bash','scripts/evaluate_test.sh'], 'argv_extra':[],
        'changes_to_eval_or_environment':False}
    try:
        if name.startswith('reference_seed'):
            seed = int(name.removeprefix('reference_seed'))
            pred = original_training(seed, 6)
            if seed == 7:
                source = reference()
                evidence['original_seed7_exact_artifact_match'] = pred == source
                evidence['original_seed7_proposed_exact_match'] = pred['experiments'][EXP]['methods'][PROPOSED] == source['experiments'][EXP]['methods'][PROPOSED]
        elif name == 'reference':
            pred = reference()
        elif name == 'better_training24':
            pred = original_training(7, 24)
        elif name == 'better_alignment':
            pred = realignment()
        elif name == 'weaker_linear':
            pred = reference()
            pred['experiments'][EXP]['methods'][PROPOSED] = copy.deepcopy(pred['experiments'][EXP]['methods']['unlearned_linear_baseline'])
        elif name == 'weaker_noquadratic':
            pred = remove_quadratic()
        else:
            pred = make_shortcut(name)
        Path('outputs/method').mkdir(parents=True, exist_ok=True)
        Path('outputs/method/predictions.json').write_text(json.dumps(pred,indent=2))
        evidence['input_sha256'] = hashlib.sha256(Path('outputs/method/predictions.json').read_bytes()).hexdigest()
        evidence['methods_on_disk'] = {exp:list(content.get('methods', {})) for exp,content in pred['experiments'].items()}
        (folder/'predictions.json').write_text(json.dumps(pred,indent=2))
        for phase in ('train','test'):
            target = Path(f'scoring/scores_{phase}.json')
            # Fresh score path: a failure must not be confused with stale success.
            target.unlink(missing_ok=True)
            if phase == 'test' and name in ('shortcut_direct_scores','shortcut_stale_scores'):
                forged = json.loads(Path('redteam/reference/initial_scores_test.json').read_text())
                forged['experiments'][EXP]['results'][PROPOSED].update(
                    atlas_accuracy_mean=1, atlas_accuracy_min=1, atlas_accuracy_std=0,
                    invalid_assignment_rate=0, gap_to_supervised_oracle=-1,
                    semantic_labels_used_for_training=0)
                target.write_text(json.dumps(forged,indent=2))
                evidence['prewritten_scores_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
            command = ['bash',f'scripts/evaluate_{phase}.sh']
            result = subprocess.run(command, text=True, capture_output=True)
            (folder/f'{phase}.log').write_text(result.stdout+result.stderr)
            evidence[f'{phase}_returncode'] = result.returncode
            evidence[f'{phase}_output_written'] = target.exists()
            if result.returncode:
                evidence[f'{phase}_error'] = result.stderr[-2200:]
            if target.exists():
                (folder/f'scores_{phase}.json').write_bytes(target.read_bytes())
                if phase == 'test' and 'prewritten_scores_sha256' in evidence:
                    evidence['prewritten_scores_survived'] = evidence['prewritten_scores_sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
            if phase == 'train':
                after_train(name)
                pred_final = json.loads(Path('outputs/method/predictions.json').read_text())
                evidence['methods_on_disk'] = {exp:list(content.get('methods', {})) for exp,content in pred_final['experiments'].items()}
                (folder/'predictions.json').write_text(json.dumps(pred_final,indent=2))
                if target.exists():
                    (folder/'scores_train_submitted.json').write_bytes(target.read_bytes())
        if (folder/'scores_test.json').exists():
            scores = json.loads((folder/'scores_test.json').read_text())
            evidence['methods_in_test_results'] = {exp:list(content['results']) for exp,content in scores['experiments'].items()}
    except Exception as exc:
        evidence['generation_error'] = repr(exc)
        evidence['traceback'] = traceback.format_exc()
        print(evidence['traceback'], flush=True)
    finally:
        evidence['elapsed_seconds'] = time.monotonic()-started
        (folder/'evidence.json').write_text(json.dumps(evidence,indent=2))
        restore(state)
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
