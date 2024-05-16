### Build a large image out of the region tiles produced by RuneLite's image dumper
import glob
import os
from PIL import Image
import time
from memory_profiler import profile, memory_usage

@profile
def buildCompositeImage():
	### Configure this before running the script
	VERSION = "2024-04-10_a"
	regionPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
	OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/composites"
	REGION_TILE_LENGTH = 64
	TILE_PIXEL_LENGTH = 4
	MAX_MAP_SIDE_LENGTH = 999 # in regions
	PLANE_COUNT = 4

	# Identify files produced by the dumper
	fileType = "/*.png"
	regionImageFilePaths =[os.path.normpath(path).replace("\\", "/") for path in glob.glob(f"{regionPath}{fileType}")]
	# print(regionImageFilePaths)

	# Range the image dimensions
	lowerX = lowerY = MAX_MAP_SIDE_LENGTH
	upperX = upperY = 0
	for regionFilePath in regionImageFilePaths:
		fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
		plane, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}
		lowerX = min(lowerX, x)
		lowerY = min(lowerY, y)
		upperX = max(upperX, x)
		upperY = max(upperY, y)

	# Remember there's a fencepost problem here, add one tile length of pixels
	compositeWidth = (upperX - lowerX + 1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
	compositeHeight = (upperY - lowerY + 1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH

	# We aren't rendering tiles from (0,0), so find the offset from unused region IDs
	hOffset = (lowerX) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH
	vOffset = (lowerY) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH

	# Push region images into the composites, per plane
	for planeNum in range(0, PLANE_COUNT):
		planeImage = Image.new('RGB', (compositeWidth, compositeHeight))
		for regionY in range(upperY, lowerY-1, -1):
			for regionX in range(lowerX, upperX+1, 1):
				targetRegionFileName = os.path.normpath(os.path.join(regionPath, f"{planeNum}_{regionX}_{regionY}.png")).replace("\\", "/")
				# If we have an image already just load it in
				if targetRegionFileName in regionImageFilePaths:
					compositeXCoord = (regionX * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - hOffset
					compositeYCoord = compositeHeight - (((regionY+1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - vOffset)
					regionImage = Image.open(targetRegionFileName)
					planeImage.paste(regionImage, (compositeXCoord, compositeYCoord))
		if not os.path.exists(OUTPUT_PATH):
			os.makedirs(OUTPUT_PATH)
		planeImage.save(os.path.join(OUTPUT_PATH,  f"plane_{planeNum}.png"))

if __name__ == "__main__":
	startTime = time.time()
	# buildCompositeImage()
	print(f"Peak memory usage: {max(memory_usage(proc=buildCompositeImage))}")
	print(f"Runtime: {time.time()-startTime}")