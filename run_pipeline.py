import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Scripts in dependency order
STEPS = [
    "etl.py",                   # raw data -> cleaned CSV
    "profit_by_segment.py",
    "loss_drivers.py",
    "dashboard_tables.py",
    "slide_charts.py",
]


def main() -> None:
    # check everything exists before running anything
    missing = [s for s in STEPS if not (BASE_DIR / s).exists()]
    if missing:
        sys.exit(f"Missing script(s) in {BASE_DIR}: {', '.join(missing)}")

    start = time.time()
    for i, script in enumerate(STEPS, start=1):
        print(f"\n[{i}/{len(STEPS)}] Running {script}")
        step_start = time.time()

        result = subprocess.run([sys.executable, str(BASE_DIR / script)], cwd=BASE_DIR)
        if result.returncode != 0:
            sys.exit(f"\nPipeline stopped: {script} failed (exit code {result.returncode}).")

        print(f"Done in {time.time() - step_start:.1f}s")

    print(f"\nPipeline finished: {len(STEPS)} steps in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()