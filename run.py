import subprocess
from pathlib import Path

cwd = Path(__file__).parent
land = cwd / "inputs/land"

layers = ["land_osm"]
exts = ["cpg", "dbf", "prj", "shp", "shx"]

if __name__ == "__main__":
    for layer in layers:
        for ext in exts:
            (land / f"{layer}.{ext}").unlink(missing_ok=True)
    subprocess.run(["python", "-m", "processing"])
    subprocess.run(["python", "sync.py"])
