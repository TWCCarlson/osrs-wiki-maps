### Build a large image out of the region tiles produced by RuneLite's image dumper
import glob
import os
import multiprocessing
import cv2
import numpy as np
import time
from memory_profiler import memory_usage

### Configure this before running the script
VERSION = "2024-04-10_a"
regionPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes"
MULTIPROCESS_ENABLE = False
REGION_TILE_LENGTH = 64
TILE_PIXEL_LENGTH = 4
MAX_MAP_SIDE_LENGTH = 999 # in regions
PLANE_COUNT = 4
REGION_PIXEL_LENGTH = REGION_TILE_LENGTH * TILE_PIXEL_LENGTH

### Identify files produced by the dumper
regionImagePaths = {
	0: list(),
	1: list(),
	2: list(),
	3: list()
}
fileType = "/*.png"
globbedPaths = [os.path.normpath(path) for path in glob.glob(f"{regionPath}{fileType}")]
for path in globbedPaths:
	fileName = os.path.splitext(os.path.basename(path))[0]
	plane, _, _ = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
	regionImagePaths[plane].append(path)

### Define empty region appearance
emptyRegion = np.zeros((REGION_PIXEL_LENGTH, REGION_PIXEL_LENGTH, 3), dtype=np.uint8)

def assemblePlane(plane, upperX, upperY, lowerX, lowerY):
	# Remember there's a fencepost problem here, add one tile length of pixels
	compositeWidth = (upperX - lowerX + 1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
	compositeHeight = (upperY - lowerY + 1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH

	# We aren't rendering tiles from (0,0), so find the offset from unused region IDs
	hOffset = (lowerX) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
	vOffset = (lowerY) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
	
	# Preallocate and paste approach
	outputImage = np.zeros((compositeHeight, compositeWidth, 3), dtype=np.uint8)
	for regionFilePath in regionImagePaths[plane]:
		fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
		_, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
		compositeXCoord = (x * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - hOffset
		compositeYCoord = compositeHeight - (((y+1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - vOffset)
		regionImage = cv2.imread(regionFilePath, cv2.IMREAD_COLOR)
		outputImage[compositeYCoord:compositeYCoord+regionImage.shape[1], compositeXCoord:compositeXCoord+regionImage.shape[0]] = regionImage
	if not os.path.exists(OUTPUT_PATH):
		os.makedirs(OUTPUT_PATH)
	cv2.imwrite(os.path.join(OUTPUT_PATH, f"plane_{plane}.png"), outputImage)

def stitchRegionImages():
	# Range the image dimensions
	lowerX = lowerY = MAX_MAP_SIDE_LENGTH
	upperX = upperY = 0
	for regionFilePath in globbedPaths:
		fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
		_, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
		lowerX = min(lowerX, x)
		lowerY = min(lowerY, y)
		upperX = max(upperX, x)
		upperY = max(upperY, y)

	planeRenderArgs = list()
	for plane in range(0, PLANE_COUNT):
		planeRenderArgs.append((plane, upperX, upperY, lowerX, lowerY))

	# Assign one core per plane image
	if MULTIPROCESS_ENABLE:
		with multiprocessing.Pool() as pool:
			pool.starmap(assemblePlane, planeRenderArgs)
	else:
		for args in planeRenderArgs:
			assemblePlane(*args)

if __name__ == "__main__":
	startTime = time.time()
	# stitchRegionImages()
	print(f"Peak memory usage: {max(memory_usage(proc=stitchRegionImages))}")
	print(f"Runtime: {time.time()-startTime}")