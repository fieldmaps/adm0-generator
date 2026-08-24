"""Sync output files to Cloudflare R2 via obstore."""

import os
import time
from logging import INFO, basicConfig, getLogger
from pathlib import Path

import duckdb
import obstore as obs
from dotenv import load_dotenv
from obstore.store import S3Store

basicConfig(level=INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = getLogger(__name__)

cwd = Path(__file__).parent
exts = ["json", "csv", "xlsx"]

load_dotenv()

BUCKET = "fieldmaps-data"

# Duplicated from app/config.py: importing app.config runs its module-level argparse.
DATA_URL = "https://data.fieldmaps.io/adm0"
LAND_WORLD = [(land, world) for land in ("osm", "usgs") for world in ("intl", "all")]
REGRESSION_THRESHOLD = 0.05  # fraction of live countries allowed to go missing

# R2 multipart uploads grow flaky with many parallel TLS streams (intermittent
# 500s / TLS BadRecordMac), so cap concurrency, use larger parts, and retry —
# obstore's built-in retries don't cover the TLS errors seen on large parquets.
CHUNK_SIZE = 64 * 1024 * 1024
MAX_CONCURRENCY = 4
MAX_RETRIES = 8


def put(store: S3Store, key: str, src: Path) -> None:
    """Upload one file with reduced concurrency, retrying transient failures."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            obs.put(
                store,
                key,
                src,
                chunk_size=CHUNK_SIZE,
                max_concurrency=MAX_CONCURRENCY,
            )
            return
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(3)


def get_store() -> S3Store:
    """Return an S3Store configured for Cloudflare R2."""
    return S3Store(
        BUCKET,
        config={
            "endpoint": os.environ["R2_ENDPOINT"],
            "region": "auto",
            "access_key_id": os.environ["R2_ACCESS_KEY_ID"],
            "secret_access_key": os.environ["R2_SECRET_ACCESS_KEY"],
        },
    )


def sync(src: Path, dest_prefix: str) -> None:
    """Upload new/changed local files and delete remote files absent locally."""
    store = get_store()

    local = {
        f.relative_to(src): f.stat().st_size
        for f in src.rglob("*")
        if f.is_file() and not f.name.startswith(".")
    }

    remote = {
        Path(obj["path"]).relative_to(dest_prefix): obj["size"]
        for obj in obs.list(store, prefix=dest_prefix).collect()
    }

    for rel, size in local.items():
        if remote.get(rel) != size:
            key = f"{dest_prefix}/{rel}"
            put(store, key, src / rel)

    for rel in remote:
        if rel not in local:
            key = f"{dest_prefix}/{rel}"
            obs.delete(store, key)


def copy(src: Path, dest_key: str) -> None:
    """Upload a single file to the given R2 key."""
    store = get_store()
    put(store, dest_key, src)


def check_regression(
    conn: duckdb.DuckDBPyConnection, land: str, world: str, issues: list[str]
) -> None:
    """Compare local adm0_src set against the live published set; flag large drops."""
    local_path = cwd / f"outputs/adm0/{land}/{world}/adm0_polygons.parquet"
    live_url = f"{DATA_URL}/{land}/{world}/adm0_polygons.parquet"
    if not local_path.exists():
        return
    try:
        live_ids = {
            r[0]
            for r in conn.execute(
                f"SELECT adm0_src FROM read_parquet('{live_url}')"
            ).fetchall()
        }
    except Exception as e:  # noqa: BLE001
        logger.info(
            "%s_%s: could not fetch live baseline (%s), skipping", land, world, e
        )
        return
    local_ids = {
        r[0]
        for r in conn.execute(
            f"SELECT adm0_src FROM read_parquet('{local_path}')"
        ).fetchall()
    }
    removed = live_ids - local_ids
    added = local_ids - live_ids
    if removed or added:
        logger.info(
            "%s_%s: %d added %s, %d removed %s",
            land,
            world,
            len(added),
            sorted(added),
            len(removed),
            sorted(removed),
        )
    if live_ids and len(removed) / len(live_ids) > REGRESSION_THRESHOLD:
        issue = (
            f"{land}_{world}: {len(removed)}/{len(live_ids)} countries missing vs live"
        )
        issues.append(issue)


if __name__ == "__main__":
    conn = duckdb.connect()
    conn.execute("INSTALL httpfs; LOAD httpfs")
    conn.execute("SET enable_progress_bar = false")
    issues: list[str] = []
    for land, world in LAND_WORLD:
        check_regression(conn, land, world, issues)
    if issues:
        msg = f"regression check: {len(issues)} issue(s), {'; '.join(issues)}"
        raise RuntimeError(msg)

    sync(cwd / "outputs/adm0", "adm0")
    for ext in exts:
        copy(cwd / f"outputs/adm0.{ext}", f"adm0.{ext}")
