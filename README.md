# ADM0 Generator

![wld_00](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_00.png)

This tool provides a flexible way to manage ADM0 boundaries, using a separation of concerns for physical and political layers. For physical boundaries, OpenStreetMap coastlines (original and simplified) provide the basis for land polygons. This is taken as-is from [osmdata.openstreetmap.de](https://osmdata.openstreetmap.de/data/land-polygons.html) without further modification. Political boundaries are delineated with an extension of the U.S. Department of State Large Scale International Boundaries (LSIB) layer from [hiu.state.gov](https://hiu.state.gov/data/). This source provides exact detail about border statuses, defining multiple classifications and guidance for proper visualization. Attributes are derived from United Nations Department of Statistics M49 standard: [unstats.un.org](https://unstats.un.org/unsd/methodology/m49/overview/).

## Download Data

Outputs from this tool can be accessed at [fieldmaps.io](https://fieldmaps.io/data/adm0).

## Usage

The only requirements are to download [this repository](https://github.com/fieldmaps/adm0-template/archive/refs/heads/main.zip) and install [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure Docker Desktop is running, and from the command line of the repository's root directory, run the following:

```shell
docker compose build
docker compose up
```

On first run, spatial source data (OpenStreetMap land polygons, U.S. State Department World Polygons, and the LSIB boundary lines) is downloaded into `tmp/download/` and then processed into the `outputs` directory. Subsequent runs reuse the cached downloads in place, so re-running the pipeline is fast. To refresh sources with newer upstream releases, delete the cache and run again: `rm -rf tmp/download/`. Per-source granularity is supported — deleting just `tmp/download/osm/` (for example) will cause only OpenStreetMap land polygons to be re-fetched on the next run. The hand-curated ADM0 line and point templates live in `inputs/` and can be edited locally to use custom boundaries, so long as they follow the same naming conventions and schemas as the originals.

## Methodology

![wld_09](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_09.png)

Due to the complexity of boundaries, international divisions are stored solely as line geometries, not polygons. The example above illustrated why this is useful, as the border status can vary at points between two ADM0 areas.

|                                       Land Polygons                                       |                                ADM0 Line & Point Template                                 |
| :---------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------: |
| ![wld_01](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_01.png) | ![wld_02](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_02.png) |

**Input Layers:** Storing boundary divisions as lines is also useful for practical purposes. With polygons, manual edits introduce the possibility of topology errors from gaps and overlaps, something much less likely to occur when editing divisions as a single line. These kinds of small manual adjustments are commonly made around coastal islands and inlets when overlaying them on top of land polygons. A companion point layer is also included that provides the ISO3 code for the area represented by lines.

|                                   ADM0 Polygon Template                                   |                               Land with Internal Divisions                                |
| :---------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------: |
| ![wld_03](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_03.png) | ![wld_04](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_04.png) |

**Intersection:** Lines are polygonized into an ADM0 layer suitable for intersecting with land. Points are joined by location to add attribute information. Since polygon-polygon intersections are a very costly spatial operation, only land polygons with internal boundary divisions are used here for efficiency. Islands wholly contained within an ADM0 polygon are added afterwards in a quick operation.

|                                       ADM0 Polygons                                       |                                    ADM0 Lines & Points                                    |
| :---------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------: |
| ![wld_05](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_05.png) | ![wld_06](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_06.png) |

**Outputs:** The resulting ADM0 polygons are also used to create derivative layers. For some cartographic maps, polygons are not as useful as points and lines used together. Output lines are clipped to represent only boundaries across land, so they can be styled separately from coastlines. Points are generated at the center of each polygon using a pole of inaccessibility algorithm, ideal for placing labels at.

|                                        All Inputs                                         |                                        All Outputs                                        |
| :---------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------: |
| ![wld_08](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_08.png) | ![wld_07](https://raw.githubusercontent.com/fieldmaps/adm0-generator/main/img/wld_07.png) |

**Comparison:** Showing inputs and outputs side by side, not much changes between them. Effectively, template boundaries are clipped to land, and points are moved to the center of each land mass.
