"""Day 9 — logging. Configure once at the entry point; getLogger(__name__) everywhere."""
import logging
import sys
from pathlib import Path

# --- what a library module does ---------------------------------------------------------
log = logging.getLogger(__name__)          # "__main__" here; "pkg.module" in a package


def process(items: list[int]) -> int:
    log.debug("processing %d items", len(items))          # lazy %-formatting
    total = 0
    for i in items:
        if i < 0:
            log.warning("negative item %s skipped", i)
            continue
        total += i
    log.info("total=%d", total)
    return total


def risky() -> None:
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("division failed")                  # includes traceback


# --- what the entry point does ----------------------------------------------------------------
if __name__ == "__main__":
    verbose = "-v" in sys.argv
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # quiet a chatty third-party logger
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # add a file handler at a different level
    fh = logging.FileHandler(Path("_app.log"), encoding="utf-8")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    process([1, -2, 3])
    risky()
    logging.getLogger().removeHandler(fh)
    fh.close()                                 # Windows can't delete a file that's still open
    print("---- _app.log ----")
    print(Path("_app.log").read_text())
    Path("_app.log").unlink()
