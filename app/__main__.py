"""Pipeline entry point — runs the configured step(s) sequentially."""

from logging import getLogger

from . import _01_download, _02_prepare, _03_build, _04_export
from .config import debug, lands, step

logger = getLogger(__name__)


def _should_run(name: str) -> bool:
    return step in (None, name)


def _process_land(land: str) -> None:
    if _should_run("_02_prepare"):
        _02_prepare.main(land)
    if _should_run("_03_build"):
        _03_build.main(land)
    if _should_run("_04_export"):
        _04_export.main(land)


logger.info("--debug=%s --step=%s --lands=%s", debug, step or "all", ",".join(lands))
logger.info("starting")

if _should_run("_01_download"):
    _01_download.main()

for land in lands:
    _process_land(land)

if _should_run("_04_export"):
    _04_export.finalize()

logger.info("finished")
