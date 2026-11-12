"""Lightweight final audit: unchanged original files and reproducible ranks."""
import hashlib
import json
import math
import statistics
from pathlib import Path


def main():
    baseline = json.loads(Path('redteam/baseline_hashes.json').read_text())
    mismatches = []
    checked = []
    for name, expected in baseline.items():
        if name == 'action.yaml':
            continue  # Required end-of-turn scheduler control, not a gym input.
        path = Path(name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        checked.append(name)
        if actual != expected:
            mismatches.append({'path': name, 'expected': expected, 'actual': actual})

    summary = json.loads(Path('redteam/summary.json').read_text())
    config = json.loads(Path('scoring/reference.json').read_text())['experiments']['scaled_manual_segmentation']
    scales = {}
    for metric, cfg in config['metrics'].items():
        if not cfg['coefficient']:
            continue
        values = [entry['metrics'][metric] for entry in summary['attempts'].values()
                  if metric in entry['metrics']]
        scale = statistics.pstdev(values)
        assert math.isclose(scale, summary['metric_std'][metric], rel_tol=1e-12)
        scales[metric] = scale
    for name, entry in summary['attempts'].items():
        gain = 0.0
        for metric, scale in scales.items():
            if metric not in entry['metrics'] or not scale:
                continue
            cfg = config['metrics'][metric]
            direction = 1 if cfg['higher_is_better'] else -1
            gain += config['weight'] * abs(cfg['coefficient']) * direction * (
                entry['metrics'][metric] - summary['reference'][metric]) / scale
        assert math.isclose(gain, entry['audit_cohort_rank_gain'], abs_tol=1e-12), name

    current_predictions_match = json.loads(Path('outputs/method/predictions.json').read_text()) == json.loads(
        Path('redteam/reference/predictions.json').read_text())
    jobs_removed = all(not Path('jobs', name).exists()
                       for name in ('b19a73fc-0f2', 'b5f1768c-58a'))
    result = {
        'starting_commit': Path('redteam/start_commit.txt').read_text().strip(),
        'initial_regular_file_hash_count': len(baseline),
        'checked_regular_files': len(checked),
        'exemptions': {'action.yaml': 'Mandatory submit/done scheduler state'},
        'mismatches': mismatches,
        'scripts_run_restored': 'scripts/run.sh' in checked and not any(
            m['path'] == 'scripts/run.sh' for m in mismatches),
        'current_predictions_equal_saved_initial_reference': current_predictions_match,
        'new_job_directories_removed_after_archival': jobs_removed,
        'independent_stdlib_rank_check': True,
        'distinct_cases': len(summary['attempts']) + len(summary['failed_runs']),
        'successful_test_cases': len(summary['attempts']),
        'failed_test_cases': len(summary['failed_runs']),
        'preexisting_special_files_and_deleted_trajectory': 'See redteam/start_status.txt; untouched',
    }
    Path('redteam/restoration_check.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    assert not mismatches and current_predictions_match and jobs_removed


if __name__ == '__main__':
    main()
