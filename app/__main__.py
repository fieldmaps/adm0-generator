"""Pipeline entry point — runs the configured step(s) sequentially."""

from logging import getLogger

from . import build, export, prepare
from .config import debug, step

logger = getLogger(__name__)

logger.info("--debug=%s --step=%s", debug, step or "all")
logger.info("starting")
if step in (None, "prepare"):
    prepare.main()
if step in (None, "build"):
    build.main()
if step in (None, "export"):
    export.main()
logger.info("finished")
