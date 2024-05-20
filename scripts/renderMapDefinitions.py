import json
import numpy as np
import cv2
import os
from collections import defaultdict
from pprint import pprint
import glob
import time
from memory_profiler import memory_usage

VERSION = "2024-04-10_a"
MAP_TILES_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
MAP_DEFS_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/worldMapCompositeDefinitions"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/mapIDs/fullplanes"
SQUARE_TILE_LENGTH = 64
TILE_PIXEL_LENGTH = 4
SQUARE_PIXEL_LENGTH = SQUARE_TILE_LENGTH * TILE_PIXEL_LENGTH
ZONE_TILE_LENGTH = 8
ZONE_PIXEL_LENGTH = ZONE_TILE_LENGTH * TILE_PIXEL_LENGTH
MAX_MAP_SIDE_LENGTH = 999 # in regions
PLANE_COUNT = 4
DEBUG_MODE = False # Draws red zone boundaries and green square boundaries on the output

def renderDisplayImages():
    # Gather the defs files
    fileType = "/*.json"
    mapDefPaths = [os.path.normpath(path) for path in glob.glob(f"{MAP_DEFS_PATH}{fileType}")]
    squareDefs = defaultdict(str)
    zoneDefs = defaultdict(str)

    # Sort the defs files in square/zone pairs
    for mapDefPath in mapDefPaths:
        fileName = os.path.splitext(os.path.basename(mapDefPath))[0]
        defType, mapID = fileName.split("_") # expecting {mapSquareDefinitions/zoneDefinitions}_{mapID}.png
        if defType == "mapSquareDefinitions":
            squareDefs[mapID] = mapDefPath
        elif defType == "zoneDefinitions":
            zoneDefs[mapID] = mapDefPath
        else:
            # Probably handle this at some point
            pass
    # Also maybe assert that dict key lengths need to match

    # Render images
    for mapID in squareDefs.keys():
        renderDisplayImage(mapID, squareDefs[mapID], zoneDefs[mapID])

def renderDisplayImage(mapID, squareDefPath, zoneDefPath):
    # Range the image dimensions
    lowerX = lowerZ = MAX_MAP_SIDE_LENGTH
    upperX = upperZ = 0

    # Load the data
    squareFile = open(squareDefPath)
    squareData = json.load(squareFile)
    zoneFile = open(zoneDefPath)
    zoneData = json.load(zoneFile)
    sourcePaths = defaultdict(set)

    for data in zoneData:
        # Get the source regions
        sourceSquareX = data["sourceSquareX"]
        sourceSquareZ = data["sourceSquareZ"]
        sourcePlane = data["minLevel"]
        sourcePath = f"{MAP_TILES_PATH}/{sourcePlane}_{sourceSquareX}_{sourceSquareZ}.png"
        if os.path.exists(sourcePath):
            sourcePaths[sourcePlane].add(sourcePath)
        # Get the display regions
        displaySquareX = data["displaySquareX"]
        displaySquareZ = data["displaySquareZ"]
        # Re-range output dimensions
        lowerX = min(lowerX, displaySquareX)
        lowerZ = min(lowerZ, displaySquareZ)
        upperX = max(upperX, displaySquareX)
        upperZ = max(upperZ, displaySquareZ)

    for data in squareData:
        # Get the source regions
        sourceSquareX = data["sourceSquareX"]
        sourceSquareZ = data["sourceSquareZ"]
        sourcePlane = data["minLevel"]
        sourcePath = f"{MAP_TILES_PATH}/{sourcePlane}_{sourceSquareX}_{sourceSquareZ}.png"
        if os.path.exists(sourcePath):
            sourcePaths[sourcePlane].add(sourcePath)
        # Get the display regions
        displaySquareX = data["displaySquareX"]
        displaySquareZ = data["displaySquareZ"]
        # Re-range output dimensions
        lowerX = min(lowerX, displaySquareX)
        lowerZ = min(lowerZ, displaySquareZ)
        upperX = max(upperX, displaySquareX)
        upperZ = max(upperZ, displaySquareZ)

    # Remember there's a fencepost problem here, add one square length of pixels
    compositeWidth = (upperX - lowerX + 1) * SQUARE_PIXEL_LENGTH
    compositeHeight = (upperZ - lowerZ + 1) * SQUARE_PIXEL_LENGTH

    # We aren't rendering tiles from (0,0), so find the offset giving the new origin
    hOffset = (lowerX) * SQUARE_PIXEL_LENGTH
    vOffset = (lowerZ) * SQUARE_PIXEL_LENGTH

    # Set background of the outputs
    outputImage = np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8)

    # Mark the squares being taken
    for data in squareData:
        # Get the source square image
        sourceSquareX = data["sourceSquareX"]
        sourceSquareZ = data["sourceSquareZ"]
        sourcePlane = data["minLevel"]
        sourceLevels = data["levels"]
        sourceImagePath = f"{MAP_TILES_PATH}/{sourcePlane}_{sourceSquareX}_{sourceSquareZ}.png"
        sourceImage = cv2.imread(sourceImagePath, flags=cv2.IMREAD_UNCHANGED)
        # Get the display location
        displaySquareX = data["displaySquareX"]
        displaySquareZ = data["displaySquareZ"]
        # Transform to the composite coordinate
        compositeSquareX = (displaySquareX * SQUARE_PIXEL_LENGTH) - hOffset
        compositeSquareZ = compositeHeight - ((displaySquareZ * SQUARE_PIXEL_LENGTH) - vOffset) - SQUARE_PIXEL_LENGTH
        # Paste the image into the output
        outputImage[compositeSquareZ:compositeSquareZ+SQUARE_PIXEL_LENGTH, compositeSquareX:compositeSquareX+SQUARE_PIXEL_LENGTH] = sourceImage
        # Debug highlight
        if DEBUG_MODE:
            cv2.rectangle(outputImage, (compositeSquareX, compositeSquareZ), (compositeSquareX+SQUARE_PIXEL_LENGTH, compositeSquareZ+SQUARE_PIXEL_LENGTH), (0,255,0), 2)

    # Mark the zones being taken
    for data in zoneData:
        # Get the source regions
        sourceSquareX = data["sourceSquareX"]
        sourceSquareZ = data["sourceSquareZ"]
        sourcePlane = data["minLevel"]
        sourceLevels = data["levels"]
        sourceZoneX = data["sourceZoneX"]
        sourceZoneZ = data["sourceZoneZ"]
        sourceImagePath = f"{MAP_TILES_PATH}/{sourcePlane}_{sourceSquareX}_{sourceSquareZ}.png"
        sourceImage = cv2.imread(sourceImagePath, flags=cv2.IMREAD_UNCHANGED)
        sourceX_px = sourceZoneX * ZONE_PIXEL_LENGTH
        sourceZ_px = SQUARE_PIXEL_LENGTH - sourceZoneZ * ZONE_PIXEL_LENGTH - ZONE_PIXEL_LENGTH
        # Crop into the specific zone
        zoneImage = sourceImage[sourceZ_px:sourceZ_px+ZONE_PIXEL_LENGTH, sourceX_px:sourceX_px+ZONE_PIXEL_LENGTH]
        # Get the display location
        displaySquareX = data["displaySquareX"]
        displaySquareZ = data["displaySquareZ"]
        displayZoneX = data["displayZoneX"]
        displayZoneZ = data["displayZoneZ"]
        # Transform to the composite coordinate
        compositeZoneX = (displaySquareX * SQUARE_PIXEL_LENGTH) - hOffset + (displayZoneX * ZONE_PIXEL_LENGTH)
        # Zones are given from bottom left origin, opencv/numpy writes with top left origin
        # Further, zones are tiled in from top left
        compositeZoneZ = compositeHeight - ((displaySquareZ * SQUARE_PIXEL_LENGTH) - vOffset + (displayZoneZ * ZONE_PIXEL_LENGTH) + ZONE_PIXEL_LENGTH)
        # Paste the image into the output
        outputImage[compositeZoneZ:compositeZoneZ+ZONE_PIXEL_LENGTH, compositeZoneX:compositeZoneX+ZONE_PIXEL_LENGTH] = zoneImage
        if DEBUG_MODE:
            cv2.rectangle(outputImage, (compositeZoneX, compositeZoneZ), (compositeZoneX+ZONE_PIXEL_LENGTH, compositeZoneZ+ZONE_PIXEL_LENGTH), (0,0,255), 1)

    outputPath = os.path.join(OUTPUT_PATH, f"mapID_{mapID}")
    if not os.path.exists(outputPath):
        os.makedirs(outputPath)
    cv2.imwrite(os.path.join(outputPath, f"plane_{0}.png"), outputImage)

    squareFile.close()
    zoneFile.close()

if __name__ == "__main__":
    startTime = time.time()
	# renderDisplayImages()
    print(f"Peak memory usage: {max(memory_usage(proc=renderDisplayImages))}")
    print(f"Runtime: {time.time()-startTime}")
    