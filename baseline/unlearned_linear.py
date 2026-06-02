from __future__ import annotations

import argparse
from pathlib import Path

from method.cycle_mgm import main as method_main


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/baseline/predictions.json")
    args = parser.parse_args()
    # The method script always includes the unlearned linear baseline in its
    # output so the same evaluator can compare methods without importing here.
    import sys

    sys.argv = [
        "cycle_mgm",
        "--output",
        args.output,
        "--trials",
        "1",
        "--train-worms",
        "8",
        "--learn-worms",
        "4",
        "--test-worms",
        "4",
        "--cells",
        "120",
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    method_main()


if __name__ == "__main__":
    main()
