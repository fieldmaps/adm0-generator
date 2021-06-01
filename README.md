# ADM0 Template

![](https://img.fieldmaps.io/adm0-template/wld_00.png)

This tool provides a flexible way to manage adm0 boundaries, using a separation of concerns for physical and political layers. For physical boundaries, OpenStreetMap coastlines provide the basis for land polygons. This is taken as-is from [osmdata.openstreetmap.de](https://osmdata.openstreetmap.de/data/land-polygons.html) without further modification. Political boundaries are delineated with a derivative of the UNmap (Global International Boundaries) layer from [data.humdata.org](https://data.humdata.org/dataset/united-nations-map). This source provides exact detail about border statuses, defining multiple classifications and guidance for proper visualization.

The rational for creating a hybrid source layer is to address one of the shortcomings of using the UNmap source itself for very high-resolution print and web maps. Coastline precision for this layer is approximately 500m in most places, making it less than ideal for maps going down to street level around shores. OpenStreetMap provides about 36x more coastline detail (1,100 MB vs 30 MB), and is also purpose built to be aligned with the rest of OSM data.

## Usage

The only requirements are to download [this repository](https://github.com/fieldmaps/adm0-template/archive/refs/heads/main.zip) and install [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure Docker Desktop is running, and from the command line of the repository's root directory, run the following:

```sh
docker compose up
```

On first run, spatial data is automatically downloaded to the `inputs` directory, where it's processed to the `outputs` directory. Afterwards, runs will reuse data in place, meant to facilitate making manual edits to local sources and seeing merged results. It's possible to use custom land polygons or custom adm0 lines, so long as they follow the same naming conventions and schemas of the originals. If files are missing from either `inputs/adm0` or `inputs/land` on subsequent runs, the missing parts will be downloaded. For example, it would be useful to delete OpenStreetMap land polygons periodically to refresh with an updated version.

## Upgrading

If a previous version of this tool has been used, old docker containers and images need to be removed so they can be re-built with a new version from the git repository. The following commands will clean up a local docker environment before running:

```sh
docker container prune -f
docker image prune -af
docker compose up
```

## Methodology

![](https://img.fieldmaps.io/adm0-template/wld_09.png)

Due to the complexity of boundaries, international divisions are stored solely as line geometries, not polygons. The example above illustrated why this is useful, as the border status can vary at points between two adm0 areas. To obtain the input lines with a voronoi-like global coverage, a [companion tool](https://github.com/fieldmaps/polygon-voronoi) is run on the original UNmap dataset and uploaded here as [lines](https://data.fieldmaps.io/adm0-template/adm0_lines.gpkg), [points](https://data.fieldmaps.io/adm0-template/adm0_points.gpkg), and [attributes](https://data.fieldmaps.io/adm0-template/adm0_attributes.xlsx).

|                     Land Polygons                      |               ADM0 Line & Point Template               |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_01.png) | ![](https://img.fieldmaps.io/adm0-template/wld_02.png) |

**Input Layers:** Storing boundary divisions as lines is also useful for practical purposes. With polygons, manual edits introduce the possibility of topology errors from gaps and overlaps, something much less likely to occur when editing divisions as a single line. These kinds of small manual adjustments are commonly made around coastal islands and inlets when overlaying them on top of land polygons. A companion point layer is also included that provides the ISO3 code for the area represented by lines.

|                 ADM0 Polygon Template                  |              Land with Internal Divisions              |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_03.png) | ![](https://img.fieldmaps.io/adm0-template/wld_04.png) |

**Intersection:** Lines are polygonized into an adm0 layer suitable for intersecting with land. Points are joined by location to add attribute information. Since polygon-polygon intersections are a very costly spatial operation, only land polygons with internal boundary divisions are used here for efficiency. Islands wholly contained within an adm0 polygon are added afterwards in a quick operation.

|                     ADM0 Polygons                      |                  ADM0 Lines & Points                   |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_05.png) | ![](https://img.fieldmaps.io/adm0-template/wld_06.png) |

**Outputs:** The resulting adm0 polygons are also used to create derivative layers. For some cartographic maps, polygons are not as useful as points and lines used together. Output lines are clipped to represent only boundaries across land, so they can be styled separately from coastlines. Points are generated at the center of each polygon using a pole of inaccessibility algorithm, ideal for placing labels at.

|                       All Inputs                       |                      All Outputs                       |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_08.png) | ![](https://img.fieldmaps.io/adm0-template/wld_07.png) |

**Comparison:** Showing inputs and outputs side by side, not much changes between them. Effectively, template boundaries are clipped to land, and points are moved to the center of each land mass.
