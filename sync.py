"""Sync output files to Cloudflare R2 via obstore."""

import os
from pathlib import Path

import obstore as obs
from dotenv import load_dotenv
from obstore.store import S3Store

cwd = Path(__file__).parent
exts = ["json", "csv", "xlsx"]

load_dotenv()

BUCKET = "fieldmaps-data"


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
            obs.put(store, key, src / rel)

    for rel in remote:
        if rel not in local:
            key = f"{dest_prefix}/{rel}"
            obs.delete(store, key)


def copy(src: Path, dest_key: str) -> None:
    """Upload a single file to the given R2 key."""
    store = get_store()
    obs.put(store, dest_key, src)


if __name__ == "__main__":
    sync(cwd / "outputs/adm0", "adm0")
    for ext in exts:
        copy(cwd / f"outputs/adm0.{ext}", f"adm0.{ext}")
