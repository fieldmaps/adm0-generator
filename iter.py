"""Iterate on one sub-step of the build/export pipeline against a snapshot.

Workflow:

    # one-time, after a successful run with --debug (intermediate tables preserved):
    cp tmp/build.duckdb tmp/build.snap.duckdb

    # per iteration (~5 sec restore + the function under test):
    uv run iter.py build intersection usgs
    uv run iter.py build polygonize usgs

The snapshot is restored to ``tmp/{step}.duckdb`` then the named sub-step's
``main(conn, land)`` is called directly, skipping every prior sub-step.

To take a fresh snapshot after intentional pipeline changes, re-run the full
step (``uv run python -m app --step build --debug``) and re-copy.
"""

# `app.config` parses sys.argv at import time, so consume iter.py's args
# before importing anything from `app`.
from argparse import ArgumentParser
from sys import argv

_parser = ArgumentParser(description=__doc__)
_parser.add_argument("step", choices=["build", "export"])
_parser.add_argument(
    "substep",
    help="Module under app/{step}/ to invoke (e.g. intersection).",
)
_parser.add_argument(
    "land",
    nargs="?",
    choices=["osm", "usgs"],
    help="Land source for the sub-step. Omit for sub-steps that take only conn.",
)
_args = _parser.parse_args()
argv[:] = argv[:1]

from importlib import import_module  # noqa: E402
from shutil import copy  # noqa: E402
from sys import exit as sys_exit  # noqa: E402

from app.config import tmp_dir  # noqa: E402
from app.utils import get_conn  # noqa: E402


def main() -> None:
    """Restore the snapshot and invoke the named sub-step."""
    snap = tmp_dir / f"{_args.step}.snap.duckdb"
    db = tmp_dir / f"{_args.step}.duckdb"
    if not snap.exists():
        sys_exit(
            f"snapshot not found: {snap}\n"
            f"run `uv run python -m app --step {_args.step} --debug` first, "
            f"then `cp {db} {snap}`"
        )

    copy(snap, db)
    db.with_suffix(".duckdb.wal").unlink(missing_ok=True)

    mod = import_module(f"app.{_args.step}.{_args.substep}")
    conn = get_conn(_args.step, reset=False)
    if _args.land is None:
        mod.main(conn)
    else:
        mod.main(conn, _args.land)
    conn.close()


if __name__ == "__main__":
    main()
