import os.path
import cache
import createCompositeImages
import createZoomedPlanes


# fetchCache()
# fetchXTEA()
# dumpMapData()
# createCompositePlanes()
# rescalePlanes()
# generateBaseTiles()
# reshapeDirectory()
# for mapID in mapIDs
#     buildMapID()
#     drawIcons()
#     sliceImage()
#     reshapeDirectory()


if __name__ == "__main__":
    """
        Build ALL maps used in the wiki from scratch
    """
    # 1. Retrieve the latest cache files and XTEA keys
    # outputDir = cache.download(f"./osrs-wiki-maps/out/mapgen/versions")
    outputDir = os.path.join(f"./osrs-wiki-maps/out/mapgen/versions", "2024-05-29_a")

    # 2. Dump map data using RuneLite
    # Call the java program to dump map data
    # When this is working, the version of the cache and xteas will need to be passed in alongside the directory
    # It should build a directory inside /mapgen/versions/ called fullplanes and dump the images there
    # It should also return that directory
    # planeImageDir = somefunction()
    planeImageDir = os.path.join(outputDir, "fullplanes/base")

    # 3. Generate the stacked composite images for higher planes
    createCompositeImages.actionRoutine(outputDir)

    # 4. Generate the zoom levels from the composite planes
    createZoomedPlanes.actionRoutine(outputDir)