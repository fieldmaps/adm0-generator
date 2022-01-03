# ADM0 Generator

![](https://img.fieldmaps.io/adm0-generator/wld_00.png)

This tool provides a flexible way to manage ADM0 boundaries, using a separation of concerns for physical and political layers. For physical boundaries, OpenStreetMap coastlines (original and simplified) provide the basis for land polygons. This is taken as-is from [osmdata.openstreetmap.de](https://osmdata.openstreetmap.de/data/land-polygons.html) without further modification. Political boundaries are delineated with an extension of the U.S. Department of State Large Scale International Boundaries (LSIB) layer from [hiu.state.gov](https://hiu.state.gov/data/). This source provides exact detail about border statuses, defining multiple classifications and guidance for proper visualization. Attributes are derived from United Nations Department of Statistics M49 standard: [unstats.un.org](https://unstats.un.org/unsd/methodology/m49/overview/).

### International

A balanced world view for use by international non-governmental organizations. Disputed areas follow recommended representation used by the [UN Clear Map](https://geoservices.un.org/Html5Viewer/index.html?viewer=clearmap). UN agencies should use official layers at the [UN Geospatial Hub](https://geoservices.un.org/webapps/geohub/).

| Layer Type | Original                                                                        | Simplified                                                                                   |
| ---------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/intl/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/intl/simplified_adm0_polygons.gpkg.zip) |
| Lines      | [Original Lines](https://data.fieldmaps.io/adm0/intl/adm0_lines.gpkg.zip)       | [Simplified Lines](https://data.fieldmaps.io/adm0/intl/simplified_adm0_lines.gpkg.zip)       |
| Points     | [Original Points](https://data.fieldmaps.io/adm0/intl/adm0_points.gpkg.zip)     | [Simplified Points](https://data.fieldmaps.io/adm0/intl/simplified_adm0_points.gpkg.zip)     |

### All Disputed Areas Disaggregated

A conservative world view that depicts all disputed areas individually. Useful if applying individual customization outside the presets generated here.

| Layer Type | Original                                                                       | Simplified                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/all/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/all/simplified_adm0_polygons.gpkg.zip) |
| Lines      | [Original Lines](https://data.fieldmaps.io/adm0/all/adm0_lines.gpkg.zip)       | [Simplified Lines](https://data.fieldmaps.io/adm0/all/simplified_adm0_lines.gpkg.zip)       |
| Points     | [Original Points](https://data.fieldmaps.io/adm0/all/adm0_points.gpkg.zip)     | [Simplified Points](https://data.fieldmaps.io/adm0/all/simplified_adm0_points.gpkg.zip)     |

### United States

World view of the United States as represented in the original Large Scale International Boundaries (LSIB) layer.

| Layer Type | Original                                                                       | Simplified                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/usa/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/usa/simplified_adm0_polygons.gpkg.zip) |
| Lines      | [Original Lines](https://data.fieldmaps.io/adm0/usa/adm0_lines.gpkg.zip)       | [Simplified Lines](https://data.fieldmaps.io/adm0/usa/simplified_adm0_lines.gpkg.zip)       |
| Points     | [Original Points](https://data.fieldmaps.io/adm0/usa/adm0_points.gpkg.zip)     | [Simplified Points](https://data.fieldmaps.io/adm0/usa/simplified_adm0_points.gpkg.zip)     |

### China

World view incorperating Hong Kong, Macau, Taiwan, and disputed areas in the Himalayas and South China Sea as part of China. Regions such as Western Sahara and Kosovo are represented based on Chinese recognition.

| Layer Type | Original                                                                       | Simplified                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/chn/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/chn/simplified_adm0_polygons.gpkg.zip) |
| Lines      | [Original Lines](https://data.fieldmaps.io/adm0/chn/adm0_lines.gpkg.zip)       | [Simplified Lines](https://data.fieldmaps.io/adm0/chn/simplified_adm0_lines.gpkg.zip)       |
| Points     | [Original Points](https://data.fieldmaps.io/adm0/chn/adm0_points.gpkg.zip)     | [Simplified Points](https://data.fieldmaps.io/adm0/chn/simplified_adm0_points.gpkg.zip)     |

### India

World view incorperating Jammu & Kashmir and disputed areas in the Himalayas as part of India. Regions such as Western Sahara and Kosovo are represented based on Indian recognition.

| Layer Type | Original                                                                       | Simplified                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/ind/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/ind/simplified_adm0_polygons.gpkg.zip) |
| Lines      | [Original Lines](https://data.fieldmaps.io/adm0/ind/adm0_lines.gpkg.zip)       | [Simplified Lines](https://data.fieldmaps.io/adm0/ind/simplified_adm0_lines.gpkg.zip)       |
| Points     | [Original Points](https://data.fieldmaps.io/adm0/ind/adm0_points.gpkg.zip)     | [Simplified Points](https://data.fieldmaps.io/adm0/ind/simplified_adm0_points.gpkg.zip)     |

### Land

Recommended for visualizing shorelines when used with point and line layers above for cartographic applications.

| Layer Type | Original                                                                       | Simplified                                                                                  |
| ---------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Polygons   | [Original Polygons](https://data.fieldmaps.io/adm0/ind/adm0_polygons.gpkg.zip) | [Simplified Polygons](https://data.fieldmaps.io/adm0/ind/simplified_adm0_polygons.gpkg.zip) |

## Usage

The only requirements are to download [this repository](https://github.com/fieldmaps/adm0-template/archive/refs/heads/main.zip) and install [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure Docker Desktop is running, and from the command line of the repository's root directory, run the following:

```sh
docker compose up
```

On first run, spatial data is automatically downloaded to the `inputs` directory, where it's processed to the `outputs` directory. Afterwards, runs will reuse data in place, meant to facilitate making manual edits to local sources and seeing merged results. It's possible to use custom land polygons or custom ADM0 lines, so long as they follow the same naming conventions and schemas of the originals. If files are missing from any inputs sub-directory on subsequent runs, the missing parts will be downloaded. For example, it would be useful to delete OpenStreetMap land polygons periodically to refresh with an updated version.

## Upgrading

If a previous version of this tool has been used, old docker containers and images need to be removed so they can be re-built with a new version from the git repository. The following commands will clean up a local docker environment before running:

```sh
docker container prune -f
docker image prune -af
docker compose up
```

## Methodology

![](https://img.fieldmaps.io/adm0-generator/wld_09.png)

Due to the complexity of boundaries, international divisions are stored solely as line geometries, not polygons. The example above illustrated why this is useful, as the border status can vary at points between two ADM0 areas.

|                      Land Polygons                      |               ADM0 Line & Point Template                |
| :-----------------------------------------------------: | :-----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-generator/wld_01.png) | ![](https://img.fieldmaps.io/adm0-generator/wld_02.png) |

**Input Layers:** Storing boundary divisions as lines is also useful for practical purposes. With polygons, manual edits introduce the possibility of topology errors from gaps and overlaps, something much less likely to occur when editing divisions as a single line. These kinds of small manual adjustments are commonly made around coastal islands and inlets when overlaying them on top of land polygons. A companion point layer is also included that provides the ISO3 code for the area represented by lines.

|                  ADM0 Polygon Template                  |              Land with Internal Divisions               |
| :-----------------------------------------------------: | :-----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-generator/wld_03.png) | ![](https://img.fieldmaps.io/adm0-generator/wld_04.png) |

**Intersection:** Lines are polygonized into an ADM0 layer suitable for intersecting with land. Points are joined by location to add attribute information. Since polygon-polygon intersections are a very costly spatial operation, only land polygons with internal boundary divisions are used here for efficiency. Islands wholly contained within an ADM0 polygon are added afterwards in a quick operation.

|                      ADM0 Polygons                      |                   ADM0 Lines & Points                   |
| :-----------------------------------------------------: | :-----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-generator/wld_05.png) | ![](https://img.fieldmaps.io/adm0-generator/wld_06.png) |

**Outputs:** The resulting ADM0 polygons are also used to create derivative layers. For some cartographic maps, polygons are not as useful as points and lines used together. Output lines are clipped to represent only boundaries across land, so they can be styled separately from coastlines. Points are generated at the center of each polygon using a pole of inaccessibility algorithm, ideal for placing labels at.

|                       All Inputs                        |                       All Outputs                       |
| :-----------------------------------------------------: | :-----------------------------------------------------: |
| ![](https://img.fieldmaps.io/adm0-generator/wld_08.png) | ![](https://img.fieldmaps.io/adm0-generator/wld_07.png) |

**Comparison:** Showing inputs and outputs side by side, not much changes between them. Effectively, template boundaries are clipped to land, and points are moved to the center of each land mass.
