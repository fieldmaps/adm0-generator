"""Pipeline entry point — runs the configured step(s) sequentially."""

from logging import getLogger

from . import build, download, export, prepare
from .config import debug, lands, step

logger = getLogger(__name__)


def _should_run(name: str) -> bool:
    return step in (None, name)


def _process_land(land: str) -> None:
    if _should_run("prepare"):
        prepare.main(land)
    if _should_run("build"):
        build.main(land)
    if _should_run("export"):
        export.main(land)


logger.info("--debug=%s --step=%s --lands=%s", debug, step or "all", ",".join(lands))
logger.info("starting")

if _should_run("download"):
    download.main()

for land in lands:
    _process_land(land)

if _should_run("export"):
    export.finalize()

logger.info("finished")
