# adm0-generator

Batch ETL pipeline that generates Administrative Level 0 (country-level) boundary datasets by combining OpenStreetMap land polygons and USGS land polygons with the U.S. State Department's LSIB political boundary lines. Outputs GeoPackage, OpenFileGDB, GeoParquet, and XLSX for each combination of land source × world view.

## Stack

- **DuckDB** with spatial extension — all spatial processing
- **gdal vector convert** — GDB and XLSX export (reads from generated GeoPackage)
- **pandas** — reads attribute CSVs, registered into DuckDB via `conn.register()`
- **httpx** — downloads input data
- **Docker** — single-service image, no database server

## Pipeline overview

`app/__main__.py` runs `download.main()` once, then iterates `for land in lands` invoking each step's `main(land)` end-to-end before moving on to the next land. Each step × land combination owns its own DuckDB file at `tmp/{land}_{step}.duckdb` (land-first to mirror the loop; created fresh on entry), so `--step` and `--land` are fully isolated and can be re-run independently. After the land loop, `export.finalize()` writes the metadata catalog.

**`download`** (`app/download.py`):

- Downloads OSM land zip, USGS land zip, LSIB GeoPackage into `tmp/download/`. Captures source publication dates atomically with each download (OSM Last-Modified header, LSIB metadata XML) and writes them to `tmp/download/{osm,lsib}/.date`. Idempotent per source: a source is fetched only when its expected extracted file (and `.date` for OSM/LSIB) is missing. To force a refresh: `rm -rf tmp/download/` (or just one source subdir).

**`prepare.main(land)`** (`app/prepare/`):

1. `preprocessing.main(conn, land)` — loads LSIB then `ST_Read`s the requested land source
2. `attributes.main(conn, land)` — loads CSV attribute tables for the requested land

Source publication dates are read from the cached `.date` files via `app.dates.get_source_dates()` (no DuckDB table); see `app/dates.py`.

**`build.main(land)`** (`app/build/`):

1. `inputs.main(conn, land)` — copies `lsib_00`/`{land}_*` from `{land}_prepare.duckdb`; loads adm0 lines/points GeoPackages; appends LSIB to lines
2. `polygonize.main(conn, land)` — unions lines → `ST_Polygonize` → joins polygons to points
3. `continents.main(conn, land)` — identifies land masses crossed by boundary lines
4. `intersection.main(conn, land)` — clips voronoi polygons to land (per-row to cap GEOS memory)

**`export.main(land)`** (`app/export/`):

1. `outputs_land.main(conn, land)` — exports land polygons (reads from `{land}_prepare.duckdb` and `{land}_build.duckdb`)
2. For each `world` in `["intl", "all"]`:
   - `polygons.main`, `points.main`, `lines.main` — final output tables
   - `outputs.main` — exports GPKG + GDB + Parquet + XLSX
   - `cleanup.main` — drops per-world tables
3. `cleanup.postprocessing_land(conn, land)` — drops this land's remaining intermediate tables

**`export.finalize()`** — runs once after all land iterations: calls `meta.main()` to write the metadata JSON/CSV/XLSX catalog. (No cross-land cleanup is needed — each per-land DuckDB file is self-contained.)

## Key patterns

### DuckDB connection

```python
from .utils import get_conn
conn = get_conn("prepare", land)  # creates tmp/{land}_prepare.duckdb, deletes if exists
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

**GeoPackage** — DuckDB COPY TO (driver name is `GPKG`, not `GeoPackage`):

```sql
COPY (SELECT * EXCLUDE id FROM "table" ORDER BY adm0_id)
TO 'file.gpkg' (FORMAT GDAL, DRIVER 'GPKG', LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom')
```

**GeoParquet** — DuckDB COPY TO:

```sql
COPY (SELECT * EXCLUDE (id, geom), geom AS geometry FROM "table" ORDER BY adm0_id)
TO 'file.parquet' (COMPRESSION ZSTD, GEOPARQUET_VERSION V2, ROW_GROUP_SIZE 1)
```

**GDB / XLSX** — `gdal vector convert` reading from the generated GeoPackage.

## Input sources

| Constant        | Source                                                     |
| --------------- | ---------------------------------------------------------- |
| `LAND_OSM_URL`  | osmdata.openstreetmap.de — land-polygons-complete-4326.zip |
| `LAND_USGS_URL` | data.fieldmaps.io — USGS land GeoPackage                   |
| `LSIB_URL`      | data.geodata.state.gov — LSIB GeoPackage                   |

## Output structure

```
outputs/adm0/{osm,usgs}/{intl,all}/
  adm0_polygons.{gpkg,gdb,parquet,xlsx}.zip / .parquet / .xlsx
  adm0_lines.{gpkg,gdb,parquet,xlsx}
  adm0_points.{gpkg,gdb,parquet,xlsx}
  adm0_voronoi.gpkg.zip      (intl only)
  adm0_clip.gpkg.zip         (intl only)
outputs/adm0/{osm,usgs}/land/
  land_polygons.{gpkg,gdb,parquet}
```

## Running

```bash
docker compose build
docker compose run app
```

Local dev (requires DuckDB spatial + GDAL installed):

```bash
uv run python -m app                              # all steps (download is fast on re-runs)
uv run python -m app --step download              # fetch sources only (skips files already in tmp/download/)
uv run python -m app --step prepare               # single step
uv run python -m app --step build --debug         # profile + preserve intermediates + dump to tmp/debug/
uv run python -m app --step build --land usgs     # iterate on one land source
STEP=build DEBUG=1 LAND=usgs uv run python -m app   # also via env vars
```

Flags:
- `--debug` / `DEBUG=1` — wraps DuckDB connection (logs wall-clock, peak RSS, duckdb-memory delta per query, coalescing consecutive same-label executes into `query xN ...` summaries); `discard()` becomes a no-op (intermediate tables persist); after each `step.main(land)`, tables are dumped under `tmp/debug/`. Layout mirrors the land-outer loop, with only the land and step as folders: per-land tables go to `tmp/debug/{land}/{step}/{table}.parquet` (with the `{land}_` prefix stripped from the filename); shared tables go to `tmp/debug/{step}/{table}.parquet`. Examples: `osm_attributes_lines` → `tmp/debug/osm/prepare/attributes_lines.parquet`; `osm_polygons_01_a_intl` → `tmp/debug/osm/export/polygons_01_a_intl.parquet`; `lsib_00` → `tmp/debug/prepare/lsib_00.parquet`; `dates` → `tmp/debug/prepare/dates.parquet`. Implied by `--step` and `--land` (any partial run is treated as iteration).
- `--step {download,prepare,build,export}` / `STEP=...` — run only the named step; default runs all four. Implies `--debug`.
- `--land {osm,usgs}` / `LAND=...` — process only one land source (default: both). Use for fast iteration; verify with both before merging. Implies `--debug`.

To refresh source data, delete the cache: `rm -rf tmp/download/`. The next run (default or `--step download`) re-fetches everything. Compare the `dates: osm=... lsib=...` log line at the top of prepare to spot drift between cached files and current source publication dates.

### Sub-step iteration with `iter.py`

To iterate on one sub-step (e.g. `app/build/intersection.py`) without re-running the prior sub-steps each cycle:

```bash
# one-time, after a successful --debug run (intermediate tables preserved):
cp tmp/usgs_build.duckdb tmp/usgs_build.snap.duckdb

# per iteration: restores the snapshot then calls the named sub-step's main(conn, land) directly
uv run iter.py build intersection usgs
DEBUG=1 uv run iter.py build intersection usgs   # with profile output
```

Re-snapshot after intentional pipeline changes (`uv run python -m app --step build --land usgs --debug` then re-`cp`).

## Coding preferences

- **GDAL CLI** — use `gdal vector convert` for vector format conversions, not `ogr2ogr`
- **Verify options against docs** — before writing any non-obvious option name (DuckDB COPY TO drivers, GDAL flags, etc.), check official docs (duckdb.org, gdal.org); never infer from analogous APIs
- **DuckDB spatial OOM** — avoid vectorized spatial joins on large GEOS geometries; use per-row Python loops passing geometry as a WKB parameter (`ST_GeomFromWKB($1)`) so DuckDB creates one GEOS object per `execute()` call instead of N per chunk; see memory for full patterns and benchmarks
- **Scalar subquery vs WKB param** — `WHERE ST_Crosses(a.geom, (SELECT geom FROM t))` OOMs but `WHERE ST_Crosses(a.geom, ST_GeomFromWKB($1))` with the WKB fetched once in Python does not: DuckDB re-evaluates a scalar subquery per vectorized chunk, creating an extra GEOS object each time; a bound param is materialized once for the whole query
