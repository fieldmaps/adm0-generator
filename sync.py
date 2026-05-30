"""Sync output files to Cloudflare R2 via obstore."""

import os
import time
from pathlib import Path

import obstore as obs
from dotenv import load_dotenv
from obstore.store import S3Store

cwd = Path(__file__).parent
exts = ["json", "csv", "xlsx"]

load_dotenv()

BUCKET = "fieldmaps-data"

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


if __name__ == "__main__":
    sync(cwd / "outputs/adm0", "adm0")
    for ext in exts:
        copy(cwd / f"outputs/adm0.{ext}", f"adm0.{ext}")
