import json
import numpy as np
import cv2
import os
from collections import defaultdict

VERSION = "2024-04-10_a"
regionPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
mapdefsPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/worldMapCompositeDefinitions"
REGION_TILE_LENGTH = 64
TILE_PIXEL_LENGTH = 4
REGION_PIXEL_LENGTH = REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
MAX_MAP_SIDE_LENGTH = 999 # in regions
PLANE_COUNT = 4
MAP_ID = 3

# Load the data
squareFile = open(os.path.join(mapdefsPath, f'mapSquareDefinitions_{MAP_ID}.json'))
squareData = json.load(squareFile)
zoneFile = open(os.path.join(mapdefsPath, f'zoneDefinitions_{MAP_ID}.json'))
zoneData = json.load(zoneFile)
regionPaths = defaultdict(set)

for data in zoneData:
    # Get the source regions
    regionX = data["sourceSquareX"]
    regionY = data["sourceSquareZ"]
    regionPlane = data["minLevel"]
    tilePath = f"{regionPath}/{regionPlane}_{regionX}_{regionY}.png"
    regionPaths[regionPlane].add(tilePath)

for data in squareData:
    # Get the source regions
    regionX = data["sourceSquareX"]
    regionY = data["sourceSquareZ"]
    regionPlane = data["minLevel"]
    tilePath = f"{regionPath}/{regionPlane}_{regionX}_{regionY}.png"
    regionPaths[regionPlane].add(tilePath)

lowerX = lowerY = MAX_MAP_SIDE_LENGTH
upperX = upperY = 0
for plane in range(0, PLANE_COUNT):
    # Range the image dimensions
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

# Create the base images
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
    # Transform the the composite coordinate
    compositeSquareX = (regionX * REGION_PIXEL_LENGTH) - hOffset
    compositeSquareY = (upperY * REGION_PIXEL_LENGTH) - (regionY * REGION_PIXEL_LENGTH)
    cv2.rectangle(outputImages[regionPlane], (compositeSquareX, compositeSquareY), (compositeSquareX+REGION_PIXEL_LENGTH, compositeSquareY+REGION_PIXEL_LENGTH), (0,255,0), 2)

# Mark the zones being taken
for data in zoneData:
    # Get the source regions
    regionX = data["sourceSquareX"]
    regionY = data["sourceSquareZ"]
    regionPlane = data["minLevel"]
    zoneX = data["sourceZoneX"]
    zoneY = data["sourceZoneZ"]
    # Transform to the composite coordinate
    compositeZoneX = (regionX * REGION_PIXEL_LENGTH) - hOffset + (zoneX * 8 * TILE_PIXEL_LENGTH)
    # Zones are given from bottom left origin, opencv writes from top left, so we need the composite height, then offset from bottom left
    compositeZoneY = (upperY * REGION_PIXEL_LENGTH) - (regionY * REGION_PIXEL_LENGTH) + ((8*8*TILE_PIXEL_LENGTH) - (zoneY * 8 * TILE_PIXEL_LENGTH + 32))
    cv2.rectangle(outputImages[regionPlane], (compositeZoneX, compositeZoneY), (compositeZoneX+32, compositeZoneY+32), (0,0,255), 1)

for plane in range(0, PLANE_COUNT):
    cv2.imshow(f"Plane_{plane} Squares", outputImages[plane])
cv2.waitKey(0)

squareFile.close()
zoneFile.close()
