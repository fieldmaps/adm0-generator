# adm0-generator

Batch ETL pipeline that generates Administrative Level 0 (country-level) boundary datasets by combining OpenStreetMap land polygons and the U.S. State Department's World Polygons (GSV-derived; pipeline id `usgs`) with the State Department's LSIB political boundary lines. Its canonical output is a local Portolan catalog of GeoParquet + PMTiles in `catalog/`; GeoPackage, OpenFileGDB, GeoParquet, and XLSX downloads in `outputs/` are derived from it, for each combination of land source × world view.

## Stack

- **DuckDB** with spatial extension — all spatial processing and all output formats (GPKG, OpenFileGDB, GeoParquet, XLSX) via `COPY TO ... FORMAT GDAL`
- **pandas** — reads attribute CSVs, registered into DuckDB via `conn.register()`
- **httpx2** — downloads input data
- **geoparquet-io**, **tylertoo**, **portolan-cli** — catalog GeoParquet writing, PMTiles, and STAC catalog management (portolan needs `tippecanoe` on PATH)
- **Docker** — single-service image (`python:3.14-slim` + pip-installed DuckDB), no database server

## Pipeline overview

`app/__main__.py` runs `_01_download.main()` once, then iterates `for land in lands` invoking each step's `main(land)` end-to-end before moving on to the next land. Each step × land combination owns its own DuckDB file at `tmp/{land}_{step}.duckdb` (land-first to mirror the loop; created fresh on entry), so `--step` and `--land` are fully isolated and can be re-run independently. After the land loop, `_04_catalog.finalize()` validates the Portolan catalog and `_05_export.finalize()` writes the metadata catalog.

**`_01_download`** (`app/_01_download/`):

1. `_01a_download.main()` — downloads OSM land zip, USGS land zip, LSIB GeoPackage into `tmp/download/`. Captures source publication dates atomically with each download (OSM Last-Modified header, LSIB metadata XML, World Polygons release folder name such as `WorldPolygon_11_4_BETA_24Feb2025`) and writes them to `tmp/download/{osm,usgs,lsib}/.date`; clears `tmp/download/usgs/` first. Always fetches fresh — no caching.

**`_02_prepare.main(land)`** (`app/_02_prepare/`):

1. `_02a_preprocessing.main(conn, land)` — loads LSIB then `ST_Read`s the requested land source
2. `_02b_attributes.main(conn, land)` — loads CSV attribute tables for the requested land

Source publication dates are read from the `.date` files written during download via `app.utils.get_source_date(source)` (no DuckDB table). `wld_date` is the LSIB date; `wld_update` is the land source's date.

**`_03_build.main(land)`** (`app/_03_build/`):

1. `_03a_inputs.main(conn, land)` — copies `lsib_00`/`{land}_*` from `{land}__02_prepare.duckdb`; loads adm0 lines/points GeoPackages; appends LSIB to lines
2. `_03b_polygonize.main(conn, land)` — unions lines → `ST_Polygonize` → joins polygons to points
3. `_03c_continents.main(conn, land)` — identifies land masses crossed by boundary lines
4. `_03d_intersection.main(conn, land)` — clips voronoi polygons to land (per-row to cap GEOS memory)

**`_04_catalog.main(land)`** (`app/_04_catalog/`):

1. For each `world` in `["intl", "all"]`:
   - `_04a_lines.main`, `_04b_polygons.main`, `_04c_points.main`: final output tables
   - `_04d_parquet.main`: writes Hilbert-sorted GeoParquet 2.0 (no bbox column) via geoparquet-io to `catalog/{cc0,odbl}/{humanitarian,disaggregated}/adm0-{polygons,lines,points}/` (land `usgs` → `cc0`, `osm` → `odbl`; world `intl` → `humanitarian`, `all` → `disaggregated`); polygons get one row per row group; voronoi (intl only) goes to `outputs/`
   - `_04e_validate.main`: checks final lines/polygons/points tables (geometry validity, lon/lat bounds, ID uniqueness, attribute-join completeness, polygon topology, points-to-polygons row parity) before world-scoped tables are dropped
   - `_04f_cleanup.main`: drops per-world tables to free memory before the next world iteration
2. `_04g_portolan.main`: builds a PMTiles file beside each catalog parquet with tylertoo, then `portolan add <collection> --pmtiles`, which registers the existing PMTiles, default style, and thumbnail

**`_04_catalog.finalize()`** runs `portolan check --data-scope local` once after all lands.

**`_05_export.main(land)`** (`app/_05_export/`): `_05a_outputs.main` copies each catalog parquet to `outputs/adm0/{land}/{world}/` and derives GPKG + GDB (EPSG:4326) + XLSX from it, verifying row counts. **`_05_export.finalize()`** calls `_05b_meta.main()` to write the metadata JSON/CSV/XLSX catalog.

## Key patterns

### DuckDB connection

```python
from .utils import get_conn
conn = get_conn("_02_prepare", land)  # creates tmp/{land}__02_prepare.duckdb, deletes if exists
```

### Table naming

All intermediate tables are prefixed by `land` and optionally `world`:

- `osm_land_00`, `usgs_lines_01`, `osm_polygons_01_a_intl`

Use double-quoted f-strings everywhere: `f'DROP TABLE IF EXISTS "{table}"'`

### Importing spatial files

```python
conn.execute(f'CREATE TABLE "{table}" AS SELECT * FROM ST_Read(\'{path}\')')
```

### Registering DataFrames

```python
conn.register("df_temp", df)
conn.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM df_temp')
conn.unregister("df_temp")
```

### DuckDB spatial function differences

`ST_Union(geom)` aggregate → `ST_Union_Agg(geom)`

`ST_Polygonize(geom)` → `ST_Polygonize(list(geom))` (takes `GEOMETRY[]`)

`ST_Dump` returns `STRUCT(geom GEOMETRY, path INTEGER[])[]` — access via `UNNEST(...).geom`:

```sql
SELECT UNNEST(ST_Dump(ST_Polygonize(list(geom)))).geom AS geom FROM ...
```

### Exporting

All exports go through DuckDB `COPY TO`. The spatial extension bundles GDAL, so no system GDAL is required.

**GeoPackage** — driver name is `GPKG`, not `GeoPackage`:

```sql
COPY (SELECT * EXCLUDE id FROM "table" ORDER BY adm0_id)
TO 'file.gpkg' (FORMAT GDAL, DRIVER 'GPKG')
```

**OpenFileGDB** — wrap geom in `ST_MakeValid` and pin `GEOMETRY_TYPE` (driver requires a single geometry type per layer):

```sql
COPY (
    SELECT * EXCLUDE (id, geom), ST_MakeValid(geom) AS geom
    FROM "table" ORDER BY adm0_id
)
TO 'file.gdb' (FORMAT GDAL, DRIVER 'OpenFileGDB', GEOMETRY_TYPE 'MULTIPOLYGON')
```

**GeoParquet**:

```sql
COPY (SELECT * EXCLUDE (id, geom), geom AS geometry FROM "table" ORDER BY adm0_id)
TO 'file.parquet' (COMPRESSION ZSTD, GEOPARQUET_VERSION V2, ROW_GROUP_SIZE 1)
```

**XLSX** — attributes only (drop geom):

```sql
COPY (SELECT * EXCLUDE (id, geom) FROM "table" ORDER BY adm0_id)
TO 'file.xlsx' (FORMAT GDAL, DRIVER 'XLSX')
```

## Input sources

| Constant        | Source                                                     |
| --------------- | ---------------------------------------------------------- |
| `LAND_OSM_URL`  | osmdata.openstreetmap.de — land-polygons-complete-4326.zip |
| `LAND_USGS_URL` | data.geodata.state.gov — World Polygons (GSV-derived)      |
| `LSIB_URL`      | data.geodata.state.gov — LSIB GeoPackage                   |

## Output structure

```
catalog/{cc0,odbl}/{humanitarian,disaggregated}/adm0-{polygons,lines,points}/
  adm0_*.parquet, adm0_*.pmtiles, adm0_*.thumb.jpg   (gitignored)
  collection.json, README.md, AGENTS.md, styles/default.json

outputs/adm0/{osm,usgs}/{intl,all}/
  adm0_polygons.{gpkg,gdb,parquet,xlsx}.zip / .parquet / .xlsx
  adm0_lines.{gpkg,gdb,parquet,xlsx}
  adm0_points.{gpkg,gdb,parquet,xlsx}
  adm0_voronoi.gpkg.zip      (intl only)
```

## Running

```bash
docker compose build
docker compose run app
```

Local dev (DuckDB spatial extension auto-installs on first run):

```bash
uv run python -m app                                    # all steps
uv run python -m app --step _01_download                # fetch sources only
uv run python -m app --step _02_prepare                 # single step
uv run python -m app --step _03_build --debug           # profile + preserve intermediates + dump to tmp/debug/
uv run python -m app --step _03_build --land usgs       # iterate on one land source
STEP=_03_build DEBUG=1 LAND=usgs uv run python -m app   # also via env vars
```

Flags:
- `--debug` / `DEBUG=1` — wraps DuckDB connection (logs wall-clock, peak RSS, duckdb-memory delta per query, coalescing consecutive same-label executes into `query xN ...` summaries); `discard()` becomes a no-op (intermediate tables persist); after each `step.main(land)`, tables are dumped under `tmp/debug/`. Layout mirrors the land-outer loop, with only the land and step as folders: per-land tables go to `tmp/debug/{land}/{step}/{table}.parquet` (with the `{land}_` prefix stripped from the filename); shared tables go to `tmp/debug/{step}/{table}.parquet`. Examples: `osm_attributes_lines` → `tmp/debug/osm/_02_prepare/attributes_lines.parquet`; `osm_polygons_01_a_intl` → `tmp/debug/osm/_04_catalog/polygons_01_a_intl.parquet`; `lsib_00` → `tmp/debug/_02_prepare/lsib_00.parquet`; `dates` → `tmp/debug/_02_prepare/dates.parquet`. Implied by `--step` and `--land` (any partial run is treated as iteration).
- `--step {_01_download,_02_prepare,_03_build,_04_catalog,_05_export}` / `STEP=...` — run only the named step; default runs all five. Implies `--debug`.
- `--land {osm,usgs}` / `LAND=...` — process only one land source (default: both). Use for fast iteration; verify with both before merging. Implies `--debug`.

### Sub-step iteration with `iter.py`

To iterate on one sub-step (e.g. `app/_03_build/_03d_intersection.py`) without re-running the prior sub-steps each cycle:

```bash
# one-time, after a successful --debug run (intermediate tables preserved):
cp tmp/usgs__03_build.duckdb tmp/usgs__03_build.snap.duckdb

# per iteration: restores the snapshot then calls the named sub-step's main(conn, land) directly
uv run iter.py _03_build _03d_intersection usgs
DEBUG=1 uv run iter.py _03_build _03d_intersection usgs   # with profile output
```

Re-snapshot after intentional pipeline changes (`uv run python -m app --step _03_build --land usgs --debug` then re-`cp`).

## Publishing

The catalog publishes to Source Cooperative at `s3://fieldmaps/international/`. Credentials are the temporary keys from the source.coop website, pasted into the repo-root `.env` as `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` (with `AWS_DEFAULT_REGION="us-east-1"`, `AWS_ENDPOINT_URL="https://data.source.coop"`). Service-account `sck_` API keys can read but not write `fieldmaps/international`.

Check the keys (expect `assumed-role/_default/...`):

```bash
env -i HOME=$HOME PATH=$PATH bash -c 'set -a; source .env; set +a; aws sts get-caller-identity --endpoint-url https://data.source.coop/.sts'
```

Push from `catalog/`:

```bash
env -i HOME=$HOME PATH=$PATH bash -c 'set -a; source ../.env; set +a; exec ../.venv/bin/portolan push s3://fieldmaps/international/ -v --max-connections 32'
```

Large files (about 100 MB and up) fail in `portolan push`: connections to `data.source.coop` drop mid-upload (TLS read failure), obstore does not retry them, and the follow-up abort fails with `SignatureDoesNotMatch` / `NoSuchBucket`, which hides the real error. For a collection that fails this way, upload its assets and `versions.json` with the AWS CLI using `aws.config` (retries, classic transfer client), then rerun the push above, which skips them and syncs metadata:

```bash
c=odbl/gaul/adm0-polygons g=polygons
env -i HOME=$HOME PATH=$PATH AWS_CONFIG_FILE=$PWD/aws.config bash -c "set -a; source .env; set +a; for f in adm0_$g.parquet adm0_$g.pmtiles adm0_$g.thumb.jpg versions.json; do aws s3 cp catalog/$c/\$f s3://fieldmaps/international/$c/\$f --only-show-errors; done"
```

`portolan push` skips some metadata (collections with no new version, intermediate `AGENTS.md`), so finish every publish by syncing all `.json`/`.md` except `versions.json`:

```bash
env -i HOME=$HOME PATH=$PATH bash -c 'set -a; source .env; set +a; aws s3 sync catalog/ s3://fieldmaps/international/ --exclude "*" --include "*.json" --include "*.md" --exclude ".portolan/*" --exclude "*/.portolan/*" --exclude "*versions.json"'
```

## Coding preferences

- **Verify options against docs** — before writing any non-obvious option name (DuckDB COPY TO drivers, GDAL driver options exposed via DuckDB, etc.), check official docs (duckdb.org, gdal.org); never infer from analogous APIs
- **DuckDB spatial OOM** — avoid vectorized spatial joins on large GEOS geometries; use per-row Python loops passing geometry as a WKB parameter (`ST_GeomFromWKB($1)`) so DuckDB creates one GEOS object per `execute()` call instead of N per chunk; see memory for full patterns and benchmarks
- **Scalar subquery vs WKB param** — `WHERE ST_Crosses(a.geom, (SELECT geom FROM t))` OOMs but `WHERE ST_Crosses(a.geom, ST_GeomFromWKB($1))` with the WKB fetched once in Python does not: DuckDB re-evaluates a scalar subquery per vectorized chunk, creating an extra GEOS object each time; a bound param is materialized once for the whole query
