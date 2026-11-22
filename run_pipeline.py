import subprocess
import sys
import time
from pathlib import Path

from src.utils import logger

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

# Scripts inside src/ in dependency order
STEPS = [
    "etl.py",                   # raw data -> cleaned CSV
    "profit_by_segment.py",
    "loss_drivers.py",
    "dashboard_tables.py",
    "slide_charts.py",
]


def main() -> None:
    # check everything exists before running anything
    missing = [s for s in STEPS if not (SRC_DIR / s).exists()]
    if missing:
        logger.error("Missing script(s) in %s: %s", SRC_DIR, ", ".join(missing))
        sys.exit(1)

    start = time.time()
    for i, script in enumerate(STEPS, start=1):
        logger.info("[%d/%d] Running %s", i, len(STEPS), script)
        step_start = time.time()

        # run as a module (python -m src.etl) so the "src." imports work
        module = f"src.{Path(script).stem}"
        result = subprocess.run([sys.executable, "-m", module], cwd=BASE_DIR)
        if result.returncode != 0:
            logger.error("Pipeline stopped: %s failed (exit code %d)", script, result.returncode)
            sys.exit(1)

        logger.info("%s finished in %.1fs", script, time.time() - step_start)

    logger.info("Pipeline finished: %d steps in %.1fs", len(STEPS), time.time() - start)


if __name__ == "__main__":
    main()