def generateTiles(version=None):
    """
        This script executes the workflow used to generate a completely new set of maps
        - Fetches most recent cache, xteas
        - Dumps the map data from the game cache as complete planes and a mapdefs file
        - Composites higher planes with lower planes
        - Rescales the planes to appropriate zoom levels
        - Slices the planes into tiles at each zoom level
        - Composes the mapIDs from the tiles
        - Inserts icons into the mapIDs
        - Slices the mapIDs into tiles at each zoom level
        - Validates the directory shape
    """
    fetchCache()
    fetchXTEA()
    dumpMapData()
    createCompositePlanes()
    rescalePlanes()
    generateBaseTiles()
    reshapeDirectory()
    for mapID in mapIDs
        buildMapID()
        drawIcons()
        sliceImage()
        reshapeDirectory()

if __name__ == "__main__":
    generateTiles()