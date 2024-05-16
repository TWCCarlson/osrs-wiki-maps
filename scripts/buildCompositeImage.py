### Build a large image out of the region tiles produced by RuneLite's image dumper
import glob
import os
from PIL import Image
import time
from memory_profiler import profile, memory_usage


# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

@profile
def buildCompositeImage():
	# Configure this before running the script
	VERSION = "2024-04-10_a"
	regionPath = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}"
	OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/composites"
	REGION_TILE_LENGTH = 64
	TILE_PIXEL_LENGTH = 4
	MAX_MAP_SIDE_LENGTH = 999 # in regions
	PLANE_COUNT = 4

	# Identify files produced by the dumper
	fileType = "*.png"
	tileImageFilePaths = glob.glob(f"{regionPath}/tiles/base/{fileType}")

	# Range the composite image's dimensions
	lowerX = lowerY = MAX_MAP_SIDE_LENGTH
	upperX = upperY = 0
	for regionFilePath in tileImageFilePaths:
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
	hOffset = (upperX + 1) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH - compositeWidth
	# Image references top left corner as origin, while Jagex uses bottom left so offset by 1 region length
	vOffset = (upperY) * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH - compositeHeight

	compositeImages = {
		0: pv.Image.black(compositeWidth, compositeHeight),
		1: pv.Image.black(compositeWidth, compositeHeight),
		2: pv.Image.black(compositeWidth, compositeHeight),
		3: pv.Image.black(compositeWidth, compositeHeight)
	}

	# Prepare to save images
	if not os.path.exists(OUTPUT_PATH):
		os.makedirs(OUTPUT_PATH)

	for regionFilePath in tileImageFilePaths:
		fileName = os.path.splitext(os.path.basename(regionFilePath))[0]
		plane, x, y = map(int, fileName.split("_"))
		regionImage = pv.Image.new_from_file(regionFilePath, access="sequential")
		# Transform region data to location in the composite image
		# Image references top left corner as origin, while Jagex uses bottom left
		compositeXCoord = (x * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - hOffset
		compositeYCoord = compositeHeight - ((y * REGION_TILE_LENGTH * TILE_PIXEL_LENGTH) - vOffset)
		if plane == 0:
			compositeImages[plane] = compositeImages[plane].insert(regionImage, compositeXCoord, compositeYCoord)
		# compositeImage = compositeImage.insert(regionImage, compositeXCoord, compositeYCoord, expand=True)
		# if not os.path.exists(OUTPUT_PATH):
		# 	os.makedirs(OUTPUT_PATH)
		# compositeImage.write_to_file(vips_filename=os.path.join(OUTPUT_PATH,  f"plane_{planeNum}.png"))
	
	for plane, compositeImage in compositeImages.items():
		compositeImage.write_to_file(vips_filename=os.path.join(OUTPUT_PATH,  f"plane_{plane}.png"))


if __name__ == "__main__":
	startTime = time.time()
	print("Starting run . . .")
	# image = buildCompositeImage()
	print(f"Max. memory usage: {max(memory_usage(proc=buildCompositeImage))}")
	print(f"Runtime: {(time.time()-startTime)}")
	time.sleep(2)