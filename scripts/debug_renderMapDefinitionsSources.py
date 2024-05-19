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
regionPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
MAP_DEFS_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/worldMapCompositeDefinitions"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/mapIDs/debug"
REGION_TILE_LENGTH = 64
TILE_PIXEL_LENGTH = 4
REGION_PIXEL_LENGTH = REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
MAX_MAP_SIDE_LENGTH = 999 # in regions
PLANE_COUNT = 4

def renderSourceImages():
    # Gather the defs files
    fileType = "/*.json"
    mapDefPaths = [os.path.normpath(path) for path in glob.glob(f"{MAP_DEFS_PATH}{fileType}")]
    squareDefs = defaultdict(str)
    zoneDefs = defaultdict(str)
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
        renderSourceImage(mapID, squareDefs[mapID], zoneDefs[mapID])

def renderSourceImage(mapID, squareDefPath, zoneDefPath):
    # Load the data
    squareFile = open(squareDefPath)
    squareData = json.load(squareFile)
    zoneFile = open(zoneDefPath)
    zoneData = json.load(zoneFile)
    regionPaths = defaultdict(set)

    for data in zoneData:
        # Get the source regions
        regionX = data["sourceSquareX"]
        regionY = data["sourceSquareZ"]
        regionPlane = data["minLevel"]
        tilePath = f"{regionPath}/{regionPlane}_{regionX}_{regionY}.png"
        if os.path.exists(tilePath):
            regionPaths[regionPlane].add(tilePath)

    for data in squareData:
        # Get the source regions
        regionX = data["sourceSquareX"]
        regionY = data["sourceSquareZ"]
        regionPlane = data["minLevel"]
        tilePath = f"{regionPath}/{regionPlane}_{regionX}_{regionY}.png"
        if os.path.exists(tilePath):
            regionPaths[regionPlane].add(tilePath)

    # Range the image dimensions
    lowerX = lowerY = MAX_MAP_SIDE_LENGTH
    upperX = upperY = 0
    for plane in range(0, PLANE_COUNT):
        for regionFilePath in regionPaths[plane]:
            fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
            _, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
            lowerX = min(lowerX, x)
            lowerY = min(lowerY, y)
            upperX = max(upperX, x)
            upperY = max(upperY, y)

    # Remember there's a fencepost problem here, add one tile length of pixels
    compositeWidth = (upperX - lowerX + 1) * REGION_PIXEL_LENGTH
    compositeHeight = (upperY - lowerY + 1) * REGION_PIXEL_LENGTH

    # We aren't rendering tiles from (0,0), so find the offset from unused region IDs
    hOffset = (lowerX) * REGION_PIXEL_LENGTH
    vOffset = (lowerY) * REGION_PIXEL_LENGTH

    # Find which images are in use
    outputImages = {
        0: np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8),
        1: np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8),
        2: np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8),
        3: np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8),
    }
    for plane in range(0, PLANE_COUNT):
        for regionFilePath in regionPaths[plane]:
            fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
            _, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
            compositeXCoord = (x * REGION_PIXEL_LENGTH) - hOffset
            compositeYCoord = compositeHeight - (((y+1) * REGION_PIXEL_LENGTH) - vOffset)
            regionImage = cv2.imread(regionFilePath, cv2.IMREAD_COLOR)
            outputImages[plane][compositeYCoord:compositeYCoord+regionImage.shape[1], compositeXCoord:compositeXCoord+regionImage.shape[0]] = regionImage 

    # Mark the squares being taken
    for data in squareData:
        # Get the source regions
        regionX = data["sourceSquareX"]
        regionY = data["sourceSquareZ"]
        regionPlane = data["minLevel"]
        regionLevels = data["levels"]
        # Transform the the composite coordinate
        compositeSquareX = (regionX * REGION_PIXEL_LENGTH) - hOffset
        compositeSquareY = (upperY * REGION_PIXEL_LENGTH) - (regionY * REGION_PIXEL_LENGTH)
        # cv2.rectangle(outputImages[regionPlane], (compositeSquareX, compositeSquareY), (compositeSquareX+REGION_PIXEL_LENGTH, compositeSquareY+REGION_PIXEL_LENGTH), (0,255,0), 2)
        for level in range(regionPlane, min(regionPlane+regionLevels, PLANE_COUNT)):
            cv2.rectangle(outputImages[level], (compositeSquareX, compositeSquareY), (compositeSquareX+REGION_PIXEL_LENGTH, compositeSquareY+REGION_PIXEL_LENGTH), (0,255,0), 2)

    # Mark the zones being taken
    for data in zoneData:
        # Get the source regions
        regionX = data["sourceSquareX"]
        regionY = data["sourceSquareZ"]
        regionPlane = data["minLevel"]
        regionLevels = data["levels"]
        zoneX = data["sourceZoneX"]
        zoneY = data["sourceZoneZ"]
        # Transform to the composite coordinate
        compositeZoneX = (regionX * REGION_PIXEL_LENGTH) - hOffset + (zoneX * 8 * TILE_PIXEL_LENGTH)
        # Zones are given from bottom left origin, opencv writes from top left, so we need the composite height, then offset from bottom left
        compositeZoneY = (upperY * REGION_PIXEL_LENGTH) - (regionY * REGION_PIXEL_LENGTH) + ((8*8*TILE_PIXEL_LENGTH) - (zoneY * 8 * TILE_PIXEL_LENGTH + 32))
        # cv2.rectangle(outputImages[regionPlane], (compositeZoneX, compositeZoneY), (compositeZoneX+32, compositeZoneY+32), (0,0,255), 1)
        for level in range(regionPlane, min(regionPlane+regionLevels, PLANE_COUNT)):
            cv2.rectangle(outputImages[level], (compositeZoneX, compositeZoneY), (compositeZoneX+32, compositeZoneY+32), (0,0,255), 1)

    outputPath = os.path.join(OUTPUT_PATH, f"mapID_{mapID}")
    for plane in range(0, PLANE_COUNT):
        # cv2.imshow(f"Plane_{plane}", outputImages[plane])
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)
        cv2.imwrite(os.path.join(outputPath, f"debug_source_{plane}.png"), outputImages[plane])

    squareFile.close()
    zoneFile.close()

if __name__ == "__main__":
    startTime = time.time()
	# renderSourceImages()
    print(f"Peak memory usage: {max(memory_usage(proc=renderSourceImages))}")
    print(f"Runtime: {time.time()-startTime}")
    