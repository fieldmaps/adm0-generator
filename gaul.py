"""Build GAUL variant lines, seeds and attributes from ``inputs/gaul/`` polygons.

Needs the land downloads (``--step _01_download``) and the LSIB humanitarian catalog.
"""

import re
import sqlite3
import subprocess
from argparse import ArgumentParser
from datetime import UTC, datetime
from logging import INFO, basicConfig, getLogger
from pathlib import Path

from duckdb import DuckDBPyConnection, connect

basicConfig(level=INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = getLogger("gaul")

cwd = Path(__file__).parent
tmp_dir = cwd / "tmp/gaul"
download_dir = cwd / "tmp/download"
out_dir = cwd / "inputs/gaul"
catalog_dir = cwd / "catalog"

LANDS = ("osm", "usgs")
LSIB_POLYGONS = {
    land: catalog_dir / f"{lic}/humanitarian/adm0-polygons/adm0_polygons.parquet"
    for land, lic in (("osm", "odbl"), ("usgs", "cc0"))
}
ISLAND_BUFFER = 0.005
LAND_TOLERANCE = 1e-7
MAX_NUDGE_ROUNDS = 5
DISPUTED = ("Sovereignty unsettled", "Joint sovereignty")
ATTRS = ["gaul0_code", "gaul0_name", "iso3_code", "map_code", "continent"]


def _topo(*args: str) -> None:
    logger.info("topo-tools %s", " ".join(args))
    subprocess.run(["topo-tools", *args], check=True)


def _cached(out: Path, src: Path) -> bool:
    """Return whether ``out`` was built after ``src`` last changed."""
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        logger.info("reusing %s", out.name)
        return True
    return False


def _topo_to(cmd: str, src: Path, out: Path) -> None:
    """Run a topo-tools command into a staging file, renamed only on success."""
    staged = out.with_name(f"{out.stem}.part.parquet")
    _topo(cmd, str(src), str(staged))
    staged.replace(out)


def clean(conn: DuckDBPyConnection, src: Path) -> Path:
    """Report coverage issues and fix them with topo-clean when present."""
    issues = tmp_dir / "src_issues.parquet"
    if not _cached(issues, src):
        _topo_to("topo-detect", src, issues)
    n = conn.execute(f"SELECT count(*) FROM read_parquet('{issues}')").fetchall()[0][0]
    logger.info("topo-detect: %d coverage issues", n)
    if n == 0:
        return src
    cleaned = tmp_dir / "src_cleaned.parquet"
    if not _cached(cleaned, src):
        _topo_to("topo-clean", src, cleaned)
    return cleaned


def extend(conn: DuckDBPyConnection, src: Path) -> Path:
    """Grow each unit into the surrounding water with topo-tools edge-extend."""
    extended = tmp_dir / "src_extended.parquet"
    if _cached(extended, src):
        return extended
    # Vertices a hair past +-180 fall outside edge-extend's clipped Voronoi cells.
    bounded = tmp_dir / "src_bounded.parquet"
    conn.execute(f"""--sql
        COPY (
            SELECT * REPLACE (CASE
                WHEN ST_XMin(geometry) < -180 OR ST_XMax(geometry) > 180
                  OR ST_YMin(geometry) < -90 OR ST_YMax(geometry) > 90
                THEN ST_Multi(ST_CollectionExtract(ST_Intersection(
                    geometry, ST_MakeEnvelope(-180, -90, 180, 90)), 3))
                ELSE geometry
            END AS geometry)
            FROM read_parquet('{src}')
        )
        TO '{bounded}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    _topo_to("edge-extend", bounded, extended)
    return extended


def load(conn: DuckDBPyConnection, src: Path, extended: Path) -> None:
    """Load cleaned GAUL L0 (``l0``) and its extended cells (``e0``)."""
    columns = ", ".join(f'"{c}"' for c in ["id", *ATTRS])
    for table, path in (("l0", src), ("e0", extended)):
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "{table}" AS
            SELECT {columns}, geometry AS geom FROM read_parquet('{path}')
        """)


def _assign(conn: DuckDBPyConnection, points: str, cells: str, out: str) -> None:
    """Write ``out`` (fid, code) for each point inside a cell, one cell per execute."""
    conn.execute(f'CREATE OR REPLACE TABLE "{out}" (fid BIGINT, code VARCHAR)')
    for code, wkb in conn.execute(
        f'SELECT code, ST_AsWKB(geom) FROM "{cells}"'
    ).fetchall():
        conn.execute(
            f"""--sql
            INSERT INTO "{out}"
            SELECT fid, $1 FROM "{points}"
            WHERE ST_Contains(ST_GeomFromWKB($2), pt)
            """,
            [code, wkb],
        )


def _islands(conn: DuckDBPyConnection, land: str) -> None:
    """Load a land source's polygons and their representative points."""
    if land == "osm":
        path = next((download_dir / "osm").rglob("land_polygons.shp"))
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "land_{land}" AS
            SELECT row_number() OVER () AS fid, geom FROM ST_Read('{path}')
        """)
    else:
        path = next((download_dir / "usgs").rglob("WorldPolygons*.gpkg"))
        with sqlite3.connect(path) as db:
            layer = next(
                name
                for (name,) in db.execute("SELECT table_name FROM gpkg_contents")
                if re.fullmatch(r"DoS_WP_\d+_\d+", name)
            )
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "land_{land}" AS
            SELECT row_number() OVER () AS fid, geom FROM (
                SELECT UNNEST(ST_Dump(geom)).geom AS geom
                FROM ST_Read('{path}', layer='{layer}')
                WHERE WP_Name IS NOT NULL
            )
        """)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE "pts_{land}" AS
        SELECT fid, ST_PointOnSurface(geom) AS pt FROM "land_{land}"
    """)


def nudge(conn: DuckDBPyConnection) -> None:
    """Move offshore islands GAUL doesn't digitize into their LSIB unit's cell."""
    conn.execute("""--sql
        CREATE OR REPLACE TABLE gaul_cells AS
        SELECT id AS code, geom FROM l0
    """)
    conn.execute("""--sql
        CREATE OR REPLACE TABLE crosswalk AS
        SELECT id AS code, upper(iso3_code) AS iso3 FROM e0
    """)
    for land in LANDS:
        _islands(conn, land)
        _assign(conn, f"pts_{land}", "gaul_cells", f"in_gaul_{land}")
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "lsib_{land}" AS
            SELECT iso_3 AS code, iso_3_grp, geometry AS geom
            FROM read_parquet('{LSIB_POLYGONS[land]}')
        """)
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "lsib_grp_{land}" AS
            SELECT DISTINCT code, iso_3_grp FROM "lsib_{land}"
        """)
        _assign(conn, f"pts_{land}", f"lsib_{land}", f"in_lsib_{land}")
    _island_bounds(conn)
    for round_ in range(1, MAX_NUDGE_ROUNDS + 1):
        moves = [m for m in _mismatches(conn) if not _kept(conn, f"land_{m[0]}", m[1])]
        logger.info("nudge round %d: %d islands to move", round_, len(moves))
        if not moves:
            break
        if round_ < MAX_NUDGE_ROUNDS:
            for land, fid, owner, target in moves:
                _move(conn, land, fid, owner, target)
    for land, fid, owner, target in moves:
        logger.warning(
            "unresolved island: %s fid %d in %s, LSIB %s", land, fid, owner, target
        )
    match_lsib(conn)
    _resolve_overlaps(conn)


def _kept(conn: DuckDBPyConnection, table: str, fid: int) -> bool:
    """Return whether a polygon touches a keep geometry, which pins it to its owner."""
    return conn.execute(
        f"""--sql
        WITH p AS (SELECT ST_GeomFromWKB(ST_AsWKB(geom)) AS geom FROM "{table}"
                   WHERE fid = $1)
        SELECT count(*) > 0 FROM keep k, p
        WHERE k.xmin <= ST_XMax(p.geom) AND k.xmax >= ST_XMin(p.geom)
          AND k.ymin <= ST_YMax(p.geom) AND k.ymax >= ST_YMin(p.geom)
          AND ST_Intersects(k.geom, p.geom)
        """,
        [fid],
    ).fetchall()[0][0]


def match_lsib(conn: DuckDBPyConnection) -> None:
    """Carve each undisputed LSIB island in another unit's cell into its own unit."""
    disputed = ", ".join(f"'{s}'" for s in DISPUTED)
    for land in LANDS:
        parts = f"lsib_parts_{land}"
        conn.execute(f"""--sql
            CREATE OR REPLACE TABLE "{parts}" AS
            SELECT row_number() OVER () AS fid, upper(iso_3) AS code,
                   upper(iso_3_grp) AS grp, status_nm IN ({disputed}) AS disputed,
                   geom, ST_PointOnSurface(geom) AS pt, ST_XMin(geom) AS xmin,
                   ST_YMin(geom) AS ymin, ST_XMax(geom) AS xmax, ST_YMax(geom) AS ymax
            FROM (
                SELECT iso_3, iso_3_grp, status_nm,
                       UNNEST(ST_Dump(geometry)).geom AS geom
                FROM read_parquet('{LSIB_POLYGONS[land]}')
            )
        """)
        conn.execute(
            "CREATE OR REPLACE TABLE ext_cells AS SELECT id AS code, geom FROM e0"
        )
        _assign(conn, parts, "ext_cells", f"part_cells_{land}")
        moves = conn.execute(f"""--sql
            SELECT p.fid, c.code AS owner,
                   arg_min(t.code, ST_Distance(p.pt, l0.geom)) AS target
            FROM "{parts}" p
            JOIN "part_cells_{land}" c USING (fid)
            JOIN crosswalk o ON o.code = c.code
            JOIN crosswalk t ON t.iso3 = p.code OR (
                t.iso3 = p.grp AND p.code NOT IN (SELECT iso3 FROM crosswalk)
            )
            JOIN l0 ON l0.id = t.code
            WHERE NOT p.disputed AND o.iso3 != t.iso3
              AND NOT starts_with(o.iso3, 'X')
            GROUP BY p.fid, c.code
        """).fetchall()
        moved = sum(
            _carve(conn, parts, fid, owner, target) for fid, owner, target in moves
        )
        logger.info("match LSIB %s: %d of %d islands moved", land, moved, len(moves))


def _carve(
    conn: DuckDBPyConnection, parts: str, fid: int, owner: str, target: str
) -> bool:
    """Move a buffered LSIB island to the target unless land or a keep shape pins it."""
    wkb, code, *bbox = conn.execute(
        f"""--sql
        SELECT ST_AsWKB(geom), code, xmin, ymin, xmax, ymax FROM "{parts}"
        WHERE fid = $1
        """,
        [fid],
    ).fetchall()[0]
    gap = conn.execute(
        f"""--sql
        SELECT min(ST_Distance(geom, ST_GeomFromWKB($1))) FROM "{parts}"
        WHERE code != $2 AND xmin <= $5 + $7 AND xmax >= $3 - $7
          AND ymin <= $6 + $7 AND ymax >= $4 - $7
        """,
        [wkb, code, *bbox, 2 * ISLAND_BUFFER],
    ).fetchall()[0][0]
    if gap == 0 or _kept(conn, parts, fid):
        return False
    buffer = ISLAND_BUFFER if gap is None else min(ISLAND_BUFFER, gap / 2)
    piece = conn.execute(
        """--sql
        WITH p AS (SELECT ST_GeomFromWKB($1) AS g),
        own AS (SELECT geom FROM e0 WHERE id = $2),
        own_land AS (SELECT geom FROM l0 WHERE id = $2)
        SELECT ST_AsWKB(ST_Difference(
            ST_Intersection(ST_Buffer(p.g, $3), own.geom),
            ST_Difference(own_land.geom, p.g)
        ))
        FROM p, own, own_land
        """,
        [wkb, owner, buffer],
    ).fetchall()[0][0]
    for table, move, params in (
        ("e0", "ST_GeomFromWKB($3)", [owner, target, piece]),
        (
            "l0",
            "ST_Intersection(ST_GeomFromWKB($3), ST_GeomFromWKB($4))",
            [owner, target, piece, wkb],
        ),
    ):
        conn.execute(
            f"""--sql
            UPDATE "{table}" SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(CASE
                WHEN id = $1 THEN ST_Difference(geom, ST_GeomFromWKB($3))
                ELSE ST_Union(geom, {move})
            END), 3))
            WHERE id IN ($1, $2)
            """,
            params,
        )
    return True


def _resolve_overlaps(conn: DuckDBPyConnection) -> None:
    """Run topo-clean on the carved cells so neighbours share exact edges."""
    carved = tmp_dir / "e0_carved.parquet"
    cleaned = tmp_dir / "e0_cleaned.parquet"
    conn.execute(f"""--sql
        COPY (SELECT id, ST_Multi(geom) AS geometry FROM e0)
        TO '{carved}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    _topo("topo-clean", str(carved), str(cleaned))
    rows = conn.execute(f"SELECT count(*) FROM read_parquet('{cleaned}')").fetchall()
    if rows[0][0] != conn.execute("SELECT count(*) FROM e0").fetchall()[0][0]:
        msg = f"topo-clean returned {rows[0][0]} cells"
        raise RuntimeError(msg)
    conn.execute(f"""--sql
        UPDATE e0 SET geom = ST_Multi(c.geometry)
        FROM read_parquet('{cleaned}') AS c WHERE e0.id = c.id
    """)


def _island_bounds(conn: DuckDBPyConnection) -> None:
    """Index every LSIB-assigned island of both lands by bbox for buffer sizing."""
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE isl_all AS
        {
        " UNION ALL ".join(
            f"""
            SELECT '{land}' AS land, fid, l.code, ST_XMin(geom) AS xmin,
                   ST_YMin(geom) AS ymin, ST_XMax(geom) AS xmax,
                   ST_YMax(geom) AS ymax, geom
            FROM "land_{land}" JOIN "in_lsib_{land}" l USING (fid)
        """
            for land in LANDS
        )
    }
    """)


def _mismatches(conn: DuckDBPyConnection) -> list[tuple[str, int, str, str]]:
    """Return (land, fid, owner, target) for off-GAUL islands in a non-LSIB cell."""
    conn.execute("""--sql
        CREATE OR REPLACE TABLE ext_cells AS
        SELECT id AS code, geom FROM e0
    """)
    moves = []
    for land in LANDS:
        _assign(conn, f"pts_{land}", "ext_cells", f"in_ext_{land}")
        rows = conn.execute(f"""--sql
            WITH cand AS (
                SELECT e.fid, e.code AS owner, cw.iso3 AS owner_iso3,
                       l.code AS lsib_iso3, g.iso_3_grp AS lsib_grp
                FROM "in_ext_{land}" e
                JOIN "in_lsib_{land}" l USING (fid)
                JOIN "lsib_grp_{land}" g ON g.code = l.code
                JOIN crosswalk cw ON cw.code = e.code
                WHERE e.fid NOT IN (SELECT fid FROM "in_gaul_{land}")
            )
            SELECT c.fid, c.owner,
                   arg_min(t.code, ST_Distance(p.pt, l0.geom)) AS target
            FROM cand c
            JOIN "pts_{land}" p USING (fid)
            JOIN crosswalk t ON t.iso3 = c.lsib_iso3 OR (
                t.iso3 = c.lsib_grp
                AND c.lsib_iso3 NOT IN (SELECT iso3 FROM crosswalk)
            )
            JOIN l0 ON l0.id = t.code
            WHERE c.owner_iso3 NOT IN (c.lsib_iso3, c.lsib_grp)
              AND NOT starts_with(c.owner_iso3, 'X')
            GROUP BY c.fid, c.owner
        """).fetchall()
        moves.extend((land, fid, owner, target) for fid, owner, target in rows)
    return moves


def _move(
    conn: DuckDBPyConnection, land: str, fid: int, owner: str, target: str
) -> None:
    """Carve a buffered island out of its owner's water cell into the target cell."""
    wkb, code, *bbox = conn.execute(
        f"""--sql
        SELECT ST_AsWKB(geom), l.code, ST_XMin(geom), ST_YMin(geom),
               ST_XMax(geom), ST_YMax(geom)
        FROM "land_{land}" JOIN "in_lsib_{land}" l USING (fid)
        WHERE fid = $1
        """,
        [fid],
    ).fetchall()[0]
    # Half the gap to the nearest other-country island, so carves never reach it.
    gap = conn.execute(
        """--sql
        SELECT min(ST_Distance(geom, ST_GeomFromWKB($1))) FROM isl_all
        WHERE code != $2 AND xmin <= $5 + $7 AND xmax >= $3 - $7
          AND ymin <= $6 + $7 AND ymax >= $4 - $7
        """,
        [wkb, code, *bbox, 2 * ISLAND_BUFFER],
    ).fetchall()[0][0]
    buffer = ISLAND_BUFFER if gap is None else min(ISLAND_BUFFER, gap / 2)
    piece = conn.execute(
        """--sql
        WITH own AS (SELECT geom FROM e0 WHERE id = $2),
        own_land AS (SELECT geom FROM l0 WHERE id = $2)
        SELECT ST_AsWKB(ST_Difference(
            ST_Intersection(ST_Buffer(ST_GeomFromWKB($1), $3), own.geom),
            own_land.geom
        ))
        FROM own, own_land
        """,
        [wkb, owner, buffer],
    ).fetchall()[0][0]
    conn.execute(
        """--sql
        UPDATE e0 SET geom = ST_Multi(ST_CollectionExtract(CASE
            WHEN id = $1
                THEN ST_Difference(geom, ST_GeomFromWKB($3))
            ELSE ST_Union(geom, ST_GeomFromWKB($3))
        END, 3))
        WHERE id IN ($1, $2)
        """,
        [owner, target, piece],
    )


def lines(conn: DuckDBPyConnection) -> None:
    """Extract shared/exterior lines of ``e0``, tagging GAUL land boundaries."""
    # package-lines only detects levels from 1 up, so ADM0 goes in as adm1.
    src = tmp_dir / "e0.parquet"
    conn.execute(f"""--sql
        COPY (
            SELECT id AS adm1_code, gaul0_name AS adm1_name, ST_Multi(geom) AS geom
            FROM e0
        )
        TO '{src}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    _topo(
        "package-lines",
        str(src),
        str(tmp_dir / "e0_lines.parquet"),
        "--code-field",
        "adm{n}_code",
        "--name-field",
        "adm{n}_name",
    )
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE e0_lines AS
        SELECT row_number() OVER () AS fid, a_code, a_name, b_code, b_name,
               geometry AS geom
        FROM read_parquet('{tmp_dir / "e0_lines.parquet"}')
    """)
    conn.execute("""--sql
        CREATE OR REPLACE TABLE split (
            fid BIGINT, kind VARCHAR, part GEOMETRY
        )
    """)
    conn.execute("""--sql
        INSERT INTO split
        SELECT fid, 'frame', geom FROM e0_lines WHERE b_code IS NULL
    """)
    npts = dict(conn.execute("SELECT id, ST_NPoints(geom) FROM l0").fetchall())
    shared = conn.execute("""--sql
        SELECT fid, a_code, b_code, ST_AsWKB(geom) FROM e0_lines
        WHERE b_code IS NOT NULL
    """).fetchall()
    for fid, a, b, wkb in shared:
        # Tag each original segment, so land/water parts keep e0's exact vertices.
        unit = a if npts[a] <= npts[b] else b
        poly = conn.execute(
            "SELECT ST_AsWKB(geom) FROM l0 WHERE id = $1", [unit]
        ).fetchall()[0][0]
        conn.execute(
            f"""--sql
            INSERT INTO split
            WITH g AS (SELECT ST_GeomFromWKB($2) AS line),
            clip AS (
                SELECT ST_Intersection(
                    ST_GeomFromWKB($3),
                    ST_Expand(ST_Envelope(line), {LAND_TOLERANCE * 10})
                ) AS poly
                FROM g
            ),
            parts AS (SELECT UNNEST(ST_Dump(line)).geom AS l FROM g),
            idx AS (
                SELECT l, UNNEST(generate_series(1, ST_NPoints(l) - 1)) AS i
                FROM parts
            ),
            segs AS (
                SELECT ST_MakeLine(
                    ST_PointN(l, i::INTEGER), ST_PointN(l, i::INTEGER + 1)
                ) AS seg
                FROM idx
            )
            SELECT $1, CASE
                WHEN ST_DWithin(
                    clip.poly, ST_LineInterpolatePoint(seg, 0.5), {LAND_TOLERANCE}
                ) THEN 'land' ELSE 'water' END, seg
            FROM segs, clip
            """,
            [fid, wkb, poly],
        )
    conn.execute("""--sql
        CREATE OR REPLACE TABLE gaul_lines AS
        SELECT row_number() OVER (ORDER BY a_code, b_code, kind) AS adm_id,
               a_code AS id_1, a_name AS gaul0_name_1,
               b_code AS id_2, b_name AS gaul0_name_2,
               kind, ST_Multi(ST_LineMerge(ST_Collect(list(part)))) AS geom
        FROM split JOIN e0_lines USING (fid)
        GROUP BY fid, a_code, a_name, b_code, b_name, kind
    """)


def points(conn: DuckDBPyConnection) -> None:
    """Seed each polygonized face with the ``e0`` cell holding its interior point."""
    conn.execute("""--sql
        CREATE OR REPLACE TABLE faces AS
        SELECT row_number() OVER () AS fid, ST_PointOnSurface(geom) AS pt FROM (
            SELECT UNNEST(ST_Dump(ST_Polygonize(list(geom)))).geom AS geom
            FROM (SELECT ST_Union_Agg(geom) AS geom FROM gaul_lines)
        )
    """)
    conn.execute("CREATE OR REPLACE TABLE ext_cells AS SELECT id AS code, geom FROM e0")
    _assign(conn, "faces", "ext_cells", "face_cells")
    conn.execute("""--sql
        CREATE OR REPLACE TABLE gaul_points AS
        SELECT f.fid, c.code AS id, f.pt AS geom
        FROM faces f
        LEFT JOIN (SELECT fid, any_value(code) AS code FROM face_cells GROUP BY fid) c
        USING (fid)
    """)
    for fid, wkb in conn.execute(
        "SELECT fid, ST_AsWKB(geom) FROM gaul_points WHERE id IS NULL"
    ).fetchall():
        conn.execute(
            """--sql
            UPDATE gaul_points SET id = (
                SELECT arg_min(id, ST_Distance(geom, ST_GeomFromWKB($2))) FROM e0
            ) WHERE fid = $1
            """,
            [fid, wkb],
        )
        logger.info("face %d seeded from its nearest cell", fid)
    conn.execute("ALTER TABLE gaul_points DROP COLUMN fid")
    for (code,) in conn.execute(
        "SELECT id FROM e0 WHERE id NOT IN (SELECT id FROM gaul_points)"
    ).fetchall():
        logger.warning("unit %s has no face", code)


def check(conn: DuckDBPyConnection) -> None:
    """Polygonize the lines and require exactly one seed point per face."""
    faces, seeded, multi = conn.execute("""--sql
        WITH faces AS (
            SELECT row_number() OVER () AS fid, geom FROM (
                SELECT UNNEST(ST_Dump(ST_Polygonize(list(geom)))).geom AS geom
                FROM (SELECT ST_Union_Agg(geom) AS geom FROM gaul_lines)
            )
        ),
        hits AS (
            SELECT f.fid, count(p.id) AS n
            FROM faces f LEFT JOIN gaul_points p ON ST_Contains(f.geom, p.geom)
            GROUP BY f.fid
        )
        SELECT count(*), count(*) FILTER (n = 1), count(*) FILTER (n > 1) FROM hits
    """).fetchall()[0]
    seeds = conn.execute("SELECT count(*) FROM gaul_points").fetchall()[0][0]
    logger.info("check: %d faces, %d seeded, %d seeds", faces, seeded, seeds)
    if faces != seeded or seeded != seeds or multi:
        msg = f"lines don't close one face per seed ({faces=}, {seeded=}, {seeds=})"
        raise RuntimeError(msg)


def write(conn: DuckDBPyConnection, *, force: bool) -> None:
    """Write lines, points and attributes to ``inputs/gaul/``."""
    lines_out = out_dir / "adm0_lines.parquet"
    if lines_out.exists() and not force:
        msg = f"{lines_out} exists and may hold manual edits; pass --force"
        raise FileExistsError(msg)
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = "(FORMAT PARQUET, COMPRESSION ZSTD, GEOPARQUET_VERSION V2)"
    conn.execute(f"COPY gaul_lines TO '{lines_out}' {opts}")
    conn.execute(f"COPY gaul_points TO '{out_dir / 'adm0_points.parquet'}' {opts}")
    columns = ", ".join(f'"{c}"' for c in ATTRS)
    attrs = conn.execute(f"SELECT id, {columns} FROM e0 ORDER BY gaul0_code").df()
    attrs.to_csv(out_dir / "adm0_attributes.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    """Build the GAUL variant inputs end to end."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite inputs/gaul")
    parser.add_argument(
        "keep", type=Path, help="geometries whose touching islands never move"
    )
    args = parser.parse_args()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(tmp_dir / "gaul.duckdb")
    conn.execute("LOAD spatial")
    conn.execute("SET geometry_always_xy = true")
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE keep AS
        SELECT geom, ST_XMin(geom) AS xmin, ST_YMin(geom) AS ymin,
               ST_XMax(geom) AS xmax, ST_YMax(geom) AS ymax
        FROM (SELECT ST_GeomFromWKB(ST_AsWKB(geom)) AS geom
              FROM read_parquet('{args.keep}'))
    """)
    src = clean(conn, out_dir / "adm0_polygons.parquet")
    extended = extend(conn, src)
    load(conn, src, extended)
    nudge(conn)
    lines(conn)
    points(conn)
    check(conn)
    write(conn, force=args.force)
    (out_dir / ".date").write_text(datetime.now(UTC).date().isoformat())
    conn.close()
    logger.info("done")


if __name__ == "__main__":
    main()
