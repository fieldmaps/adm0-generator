# ADM0 Template

![](https://img.fieldmaps.io/adm0-template/wld_00.png)

This tool provides a flexible way to manage ADM0 boundaries by using a separation of concerns for physical and cultural layers. For physical boundaries, OpenStreetMap coastlines provide the basis for land polygons. This is taken as-is from [osmdata.openstreetmap.de](https://osmdata.openstreetmap.de/download/land-polygons-complete-4326.zip) without further modification. Cultural boundaries are deliniated with a derivative of the UNmap (Global International Boundaries) layer from [data.humdata.org](https://data.humdata.org/dataset/united-nations-map). This source provides exact detail about border statuses, providing multiple classifications and guidance for proper visualization.

The rational for creating a hybrid source layer is to address some of the shortcommings of using the UNmap itself directly for very high resolution viewing. Coastline precision for this layer is approximately 500m for most places, making it less than ideal for web maps going down to street level. In this regard, OpenStreetMap coastlines provide about 18x more detail (1,100 MB vs 60 MB), and are also purpose built for use with the rest of OSM data.

## Usage

The only requirements are to download [this repository](https://github.com/fieldmaps/adm0-template/archive/refs/heads/main.zip) and install [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure Docker Desktop is running, and from the command line of the repository's root directory, run the following:

```sh
docker compose up
```

On first run, files are automatically downloaded to the included `inputs` directory, where they'll be processed into the `outputs` directory. Afterwards, runs will reuse files in place, meant to facilitate making manual edits to local sources and seeing merged results. It's possible to use custom land polygons or custom adm0 lines, so long as they follow the same file formats and schemas of the originals. If files are missing from either `inputs/adm0` or `inputs/land` on subsequent runs, the missing parts will be downloaded. This would be useful for refreshing OpenStreetMap land polygons with an updated version.

## Upgrading

If a previous version of this tool has been used, old docker containers and images need to be removed so they can be re-built with a new version from the git repository. The following commands will clean up a local docker environment before running:

```sh
docker container prune -f
docker image prune -af
docker compose up
```

## Methodology

![](https://img.fieldmaps.io/adm0-template/wld_09.png)

Due to the complexity of border statuses, international divisions are stored solely in line geometries, not polygons. The example above illustrated why this is useful, as the border status can vary even between the same two countries. To obtain the lines with a voronoi-like global coverage, a [companion tool](https://github.com/fieldmaps/polygon-voronoi) is run on the original UNmap dataset. This is then uploaded [here](https://data.fieldmaps.io/adm0_template.zip).

|                     Land Polygons                      |              ADM0 Lines & Points Template              |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_01.png) | ![](https://img.fieldmaps.io/adm0-template/wld_02.png) |

**Input Layers:** Storing boundary divisions are lines is also useful for practical purposes. With polygons there is the possibility to introduce topology errors from gaps and overlaps, something much less likely to occur when editing divisions as a single line. These kind of small manual adjustments are commonly made around coastal islands and inlets when overlaying them on top of land polygons. A companion point layer is also included that provides the ISO3 code for the area represented by lines.

|                 ADM0 Polygon Template                  |              Land with Internal Divisions              |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_03.png) | ![](https://img.fieldmaps.io/adm0-template/wld_04.png) |

**Intersection:** Lines are polygonized into an ADM0 layer suitable for intersecting with land polygons. Points are joined by location to add attribute information. Since intersections are a very costly spatial operation, only land polygons with internal divisions are used here to save time. Islands that are wholly contained within the ADM0 polygon are added afterwards in a quick operation.

|                     ADM0 Polygons                      |                  ADM0 Lines & Points                   |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_05.png) | ![](https://img.fieldmaps.io/adm0-template/wld_06.png) |

**Outputs:** The resulting ADM0 polygons are also used to create derivitave layers. For making cartographic web maps, polygons are actually not all that useful. Instead, clipped lines are taken to give more control over styling of different boundary statuses. Points are generated at the center of each polygon using a pole of inaccessibility algorithm, ideal for placing labels at.

|                       All Inputs                       |                      All Outputs                       |
| :----------------------------------------------------: | :----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-template/wld_08.png) | ![](https://img.fieldmaps.io/adm0-template/wld_07.png) |

**Comparison:** Showing inputs and outputs side by side, not much changes between them. Effectively, boundaries are clipped to land, and points are moved to the center of each land mass.
