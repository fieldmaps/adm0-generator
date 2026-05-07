"""Iterate on one sub-step of the build/export pipeline against a snapshot.

Workflow:

    # one-time, after a successful run with --debug (intermediate tables preserved):
    cp tmp/usgs__03_build.duckdb tmp/usgs__03_build.snap.duckdb

    # per iteration (~5 sec restore + the function under test):
    uv run iter.py _03_build _03d_intersection usgs
    uv run iter.py _03_build _03b_polygonize usgs

The snapshot is restored to ``tmp/{land}_{step}.duckdb`` then the named sub-step's
``main(conn, land)`` is called directly, skipping every prior sub-step.

To take a fresh snapshot after intentional pipeline changes, re-run the full
step (``uv run python -m app --step _03_build --land usgs --debug``) and re-copy.
"""

# `app.config` parses sys.argv at import time, so consume iter.py's args
# before importing anything from `app`.
from argparse import ArgumentParser
from sys import argv

_parser = ArgumentParser(description=__doc__)
_parser.add_argument("step", choices=["_03_build", "_04_export"])
_parser.add_argument(
    "substep",
    help="Module under app/{step}/ to invoke (e.g. _03d_intersection).",
)
_parser.add_argument("land", choices=["osm", "usgs"])
_args = _parser.parse_args()
argv[:] = argv[:1]

from importlib import import_module  # noqa: E402
from shutil import copy  # noqa: E402
from sys import exit as sys_exit  # noqa: E402

from app.config import tmp_dir  # noqa: E402
from app.utils import get_conn  # noqa: E402


def main() -> None:
    """Restore the snapshot and invoke the named sub-step."""
    snap = tmp_dir / f"{_args.land}_{_args.step}.snap.duckdb"
    db = tmp_dir / f"{_args.land}_{_args.step}.duckdb"
    if not snap.exists():
        sys_exit(
            f"snapshot not found: {snap}\n"
            f"run `uv run python -m app --step {_args.step} "
            f"--land {_args.land} --debug` first, then `cp {db} {snap}`"
        )

    copy(snap, db)
    db.with_suffix(".duckdb.wal").unlink(missing_ok=True)

    mod = import_module(f"app.{_args.step}.{_args.substep}")
    conn = get_conn(_args.step, _args.land, reset=False)
    mod.main(conn, _args.land)
    conn.close()


if __name__ == "__main__":
    main()
