import subprocess
from pathlib import Path

cwd = Path(__file__).parent
exts = ["json", "csv", "xlsx"]


def sync(src, dest):
    subprocess.run(
        [
            "rclone",
            "sync",
            "--exclude=.*",
            "--progress",
            "--s3-no-check-bucket",
            "--s3-chunk-size=256M",
            src,
            dest,
        ]
    )


def copy(src, dest):
    subprocess.run(
        [
            "rclone",
            "copyto",
            "--s3-no-check-bucket",
            "--s3-chunk-size=256M",
            src,
            dest,
        ]
    )


if __name__ == "__main__":
    sync(cwd / "outputs/adm0", "r2://fieldmaps-data/adm0")
    for ext in exts:
        copy(cwd / f"outputs/adm0.{ext}", f"r2://fieldmaps-data/adm0.{ext}")
