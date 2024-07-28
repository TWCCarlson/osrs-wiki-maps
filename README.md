# osrs-wiki-maps
A set of tools for generating map images for the OSRS wiki.

These scripts perform 3 major steps to produce complete tile sets which represent OSRS MapIDs:

1. Fetch a cache from the OpenRS2 archive
2. Dump game data from the cache
3. Use game data to produce the OSRS Wiki's Leaflet-compatible tiles

Some options which modify the output are configurable.

# Installation

Python scripts are written with type hint syntax introduced in 3.10, so ensure your Python version is 3.10+.

To manually dump data from the cache, ensure you have access to a [built version of RuneLite greater than 1.10.26-SNAPSHOT](https://github.com/runelite/runelite/wiki/Building-with-IntelliJ-IDEA). Running the `MapExport.java` requires Java to be installed.

To manually process the game data and produce tile images, first [install Libvips depending on your OS](https://www.libvips.org/install.html). Pyvips is a Python wrapper for the Libvips image processing library, and requires the bindings to be present. The scripts detect which supported OS (Windows or Linux) you are using and import Pyvips correctly.

> [!TIP]
> Pyvips is installed in one of two modes. If development headers for Libvips exist and there is a C compiler, it will try to use API mode which is up to 20% faster. Otherwise it will use ABI mode but still need access to the library. It is simpler to install in API mode on Linux.

Also, run `pip install -r requirements.txt`.

# Running the scripts

To fetch the latest cache, run:
```
python scripts/buildWikiMaps.py getCache
```

To fetch a specific cache version, supply the date in a format `YYYY-MM-DD_c` where `c` is the zero-indexed release count in that day (typically there is only one release). Perhaps:
```
python scripts/buildWikiMaps.py getCache 2024-07-24_0
```

With the cache and xteas downloaded, a folder matching the version string will be created, appended with an identifying letter. This folder name will be passed as an argument specifying the working directory for the remaining operations:

```
Found cache 1859 from 2024-07-24

Downloading xteas...
2s elapsed.

Downloading cache...
13s elapsed.

Cache saved to ./osrs-wiki-maps/out/mapgen/versions\2024-07-24_0_e
```

Next, run `MapExport.java`, which can be found in the `./osrs-wiki-maps/src/...` directory. This creates the plane and map icon images directly from the cache. It also dumps the definitions files which dictate how maps are assembled. By way of example, the GitHub Actions workflow looks like:

```
mvn -q clean package
java -jar target/osrs-wiki-maps-1.10.26-shaded.jar $CACHE_VER
```

where `$CACHE_VER` is the working directory name returned by the cache download script (2024-07-24_0_e). Of course, other methods of running `MapExport.java` work.

The large, single images produced by the map exporter are nice, but need to be sliced into the 256x256px tiles to be used by Leaflet. To do this, run:

```
python scripts/buildWikiMaps.py createBaseTiles 2024-07-24_0_e
```

again supplying the working directory as an argument. This should produce a large number of tiles located in the working directory's `tiles/base/2` folder.

With the base tiles produced, all that remains is to build all the MapIDs defined in the cache dump:

```
python scripts/buildWikiMaps.py buildAllMapIDs 2024-07-24_0_e
```

The output files for a particular MapID and zoom level are found in the working directory under: `tiles/rendered/<MapID>/<ZoomLevel>`

The image file names will match the wiki tile lookup convention of `<plane>_<x>_<y/z>.png`.

# Configuring Runs

The scripts make references to a configuration file: `mapBuilderConfig.json`. There are some options which can be modified that change the appearance of the output:

### Image Compositing Options

Output images of high planes are the plane image stacked overtop a composite image of all the planes beneath it. Options are provided for styling the underlying planes.

| **Option Name** | Description                                                                                                                                     | Default Value |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| "transparencyColor"      | Pixel value to be treated as background by pyvips. Supplied as a single 0-255 int or [R,G,B]. Backgound pixels are ignored when styling images. | 0             |
| "transparencyTolerance"  | The integer distance from the background color within which pixels will be ignored. Supplied as a single 0-255 int or [R,G,B]                   | 0             |
| "brightnessFraction"     | The % by which the brightness of composited images is modified. Less than 1.0 darkens the image.                                                | 1.0           |
| "contrastFraction"       | The % by which the contrast of composited images is modified. More than 1.0 sharpens the image.                                                 | 1.0           |
| "grayscaleFraction"      | The % of grayscaling applied to composited images. 1.0 is complete grayscale, while 0.0 results in no change.                                   | 0.2           |
| "blurRadius"             | The radius, in pixels, of blur to be applied to composited images.                                                                              | 1             |

### Zoom Options

To produce tiles at different zoom levels the complete image is zoomed. When this is done a choice needs to be made about the kernel used to calculate the value of pixels after rescaling. The "base" level of zoom is 2, which is equivalent to what is dumped from the cache. Therefore the setting for "2" is ignored.

| **ZOOM_OPTS["kernels"]** | Description                           | Default Value |
|--------------------------|---------------------------------------|---------------|
| "-3"                     | Kernel used to create zoom level -3 | "linear"      |
| "-2"                     | Kernel used to create zoom level -2 | "linear"      |
| "-1"                     | Kernel used to create zoom level -1 | "linear"      |
| "0"                      | Kernel used to create zoom level 0  | "linear"      |
| "1"                      | Kernel used to create zoom level 1  | "linear"      |
| "2"                      | Kernel used to create zoom level 2  | "nearest"     |
| "3"                      | Kernel used to create zoom level 3  | "nearest"     |

### Icon Options

Icons are drawn directly onto the tile images. To control whether a zoom level has icons drawn to it, use these options.

| **ICON_OPTS["zoomLevelHasIcons"]** | Description                            | Default Value |
|------------------------------------|----------------------------------------|---------------|
| "-3"                               | Toggle icon rendering on zoom level -3 | false         |
| "-2"                               | Toggle icon rendering on zoom level -2 | false         |
| "-1"                               | Toggle icon rendering on zoom level -1 | false         |
| "0"                                | Toggle icon rendering on zoom level 0  | true          |
| "1"                                | Toggle icon rendering on zoom level 1  | true          |
| "2"                                | Ignored                                | true          |
| "3"                                | Toggle icon rendering on zoom level 3  | true          |

Additionally, it is possible to configure icon rendering so that icons from other planes are rendered on an image. To do this, define a list of the planes from which icons should be taken while rendering a specific plane. Currently, the icons are rendered in the order given in the list, such that for a list [0, 1], icons from plane 1 will be drawn on top of icons from plane 0.

| **ICON_OPTS["planeHasIconsFromPlane"]** | Description                          | Default Value |
|-----------------------------------------|--------------------------------------|---------------|
| "0"                                     | Plane-group icons to draw on plane 0 | [0, 1, 2, 3]  |
| "1"                                     | Plane-group icons to draw on plane 1 | [1]           |
| "2"                                     | Plane-group icons to draw on plane 2 | [2]           |
| "3"                                     | Plane-group icons to draw on plane 3 | [3]           |

Finally, the size of an icon is a fixed value. For lower zooms, this means the icons will be drawn larger relative to the map.

| **Icon Options** | Description                     | Default Value |
|------------------|---------------------------------|---------------|
| "iconSize"       | Size, in pixels, of drawn icons | 15            |


# How it works

### vips

Pyvips is a library that wraps Libvips, a threaded (fast) and low-memory image processing library. The fundamental behavior is that image processing operations are pipelines which only execute when an end point is defined, e.g. `.write_to_file(fileName)`

As a result, the execution of image processing tasks is efficient if care is taken to correctly manage the pipelines, avoiding unnecessary repetition of tasks.

### MapID Builder

Before anything is done, icon definitions are parsed. See Icon Insertion for more details.

Next, the map definitions are loaded. Map definitions from the game cache come in two forms. 

MapSquare definitions:
```
{
    "minLevel": 0,
    "levels": 4,
    "sourceSquareX": 33,
    "sourceSquareZ": 79,
    "displaySquareX": 33,
    "displaySquareZ": 79,
    "groupId": 846,
    "fileId": 0
},
```

and MapZone definitions:
```
{
    "sourceZoneX": 7, # Relative to the square
    "sourceZoneZ": 3,
    "displayZoneX": 7,
    "displayZoneZ": 3,
    "minLevel": 0,
    "levels": 1,
    "sourceSquareX": 47,
    "sourceSquareZ": 149,
    "displaySquareX": 47,
    "displaySquareZ": 149,
    "groupId": 839,
    "fileId": 0
},
```

The instructions here specify a particular MapSquare or MapZone should be selected (sourced) and then drawn (displayed) at a particular location. Each MapID is defined by lists of squares or zones to use in this manner. Only the squares or zones specified by the definition are drawn.

The `minLevel` value specifies the lowest source plane to be captured by the definition. `levels` specifies how many levels above that source plane should be captured by the definition. This means that for the above MapZone definition only plane 0 is captured, while for the above MapSquare definition planes 0, 1, 2, and 3 are all captured. Squares and zones from each plane are be placed in the *lowest plane with an available square or zone* possible. As an example,

1. Definition A is read in, specifying a square should be drawn at (10,10)
2. Plane 0 (10,10) is reserved by definition A
3. Definition B is read in, specifying a square should be drawn at (10,10)
4. Plane 0 (10,10) is already reserved by definition A
5. Plane 1 (10,10) is reserved by definition B

On a per-mapID basis these definitions are extracted from the `wikiWorldMapDefinitions.json` file dumped by the `MapExport.java` program. Before proceeding, the script checks for overrides given in the `user_world_defs.json` file. An override is a complete overwriting of the definitions, and must be defined in a manner that fully replaces the game's definitions.

The selected definitions are then parsed into data classes. The resulting set of data classes is then used to initialize the definitions manager. Upon initialization, the definitions manager sorts the definitions using the `groupId` value, where lower values are rendered first. The primary function of the definitions manager is to inform the map builder of the proper order in which to render definitions.

This data is then passed the map builder. The map builder uses it to construct the smallest possible *mosaic* which will fit all the display data, in units of whole squares. This mosaic will be filled in using the definitions and eventually merged into one larger image. The mosaic is preallocated with "blank" definitions to be replaced.

At the map builder level, mosaic elements can consist of MapSquares, MapSquareOfZones, or empty squares. A MapSquare is defined by a definition and an image. A MapSquareOfZones is defined as a mosaic of zones which compose a square. It is handled in much the same way as the MapID mosaic, but is merged into a square-sized image to then be merged again into the MapID-sized image.

Definitions are allocated into cells of the mosaic until all definitions in the manager have been read in. Once this is done, the images relating to each definition can be loaded and rendered, and the resulting mosaic merged into one large image.

> [!NOTE]
> The "debug" MapID (-1) skips these steps because it is identical to the images dumped from the cache, saving many minutes.

At this point it is beneficial to temporarily save the image to disk, effectively starting a new pipeline from this point. This is because the image composition step would otherwise require rendering the same base image multiple times for styling and stacking fresh copies.

With the MapID's plane image saved the builder then assembles composite images such that plane 1 is drawn overtop a styled version of plane 0, plane 2 is drawn overtop a styled version of plane 1 drawn over plane 0, and so on. All underlying planes are styled together, and the backgrounds of higher plans are ignored using a mask.

With the composite image produced, the pipeline is again restarted before zooming to reduce the number of pipelines run. For each zoom level specified in the configuration file, the image is rescaled by a factor of `2**<zoomLevel>/2**<baselineZoom>`. The baseline zoom used on the wiki maps is `2`.

Each rescaled image is then sliced up into Leaflet-compatible tiles using a Libvpis function called `dzsave`, which slices images into Google-maps style tiles. The resulting directory doesn't have the correct structure or file names for OSRS purposes (`dzsave` operates from the top left while Jagex uses a bottom left origin). Therefore it is coerced into the form:
`tiles/rendered/<MapID>/<zoomLevel>/<plane>_<x>_<y>.png`.

Finally, a supplementary file called `basemaps.json` is added to. The data here is used to inform Leaflet of the `name` of the MapID, the `bounds` of the tile map, and the `center` of the map (where the viewport is initially placed).

All of these steps are repeated for each MapID to produce a complete tile set for the cache. The `user_world_defs.json` file may also be modified to contain additional "custom" MapIDs, [as the Wiki does](https://oldschool.runescape.wiki/w/RuneScape:Map/mapIDs).

### Icon Insertion

Before the map tiles are created the `minimapIcons.json` file, which specifies the location definitions for icons, is loaded into the IconManager. This is done ahead of time because these values do not change but need to be referenced by all MapIDs. An icon definition looks like:

```
{
    "position": {
        "x": 3107,
        "y": 3012,
        "z": 0
    },
    "spriteId": 1456
},
```
where `x` and `y` are the game tile the icon belongs to, `z` is the plane, and the `spriteId` identifies which image in the `icons` directory to use.

As part of initializing the manager, the icon definitions are bucketed into their owner squares and zones. This makes answering the question "What icons are in this area?" easy and fast later on.

Additionally, the display coordinates (in pixels) are calculated and used to determine whether the icon, at a particular zoom level, would spill over into another map tile.

Icons are inserted after the tile sets for each MapID are created because their size (in pixels) is invariant with zoom level (and thus cannot be placed before scaling operations).

First the icon manager is queried against the definitions in the map builder's mosaic. This returns both the icons located in each tile and the icons which overflow into the tile. This data is used to get a list of which tiles will need icons to be inserted.

The list of tiles is then iterated, and icons inserted according to their calculated positions relative to the tile. If a tile is meant to have an icon but was not rendered by the map builder (i.e. an icon overflows outside the definition boundaries) a new blank tile is created instead.

With the icons inserted, the tile is saved. Due to the nature of Pyvips data streaming, the original tile name needs to be changed before loaded. Otherwise, the pipeline would copy and paste data from the same file and fail. The renamed tile is deleted after the version with icons is saved.

# Automation
This repository leverages GitHub Actions to automate the production of a rendered set of game tiles and the `basemaps.json` file. The GitHub Action executes on a weekly basis, producing a release containing the most recent map tiles.
