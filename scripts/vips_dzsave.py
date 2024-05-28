### Create a deepzoom pyramid from the full plane images
import glob
import os
import time
from memory_profiler import memory_usage
import multiprocessing

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

### Configure this before running the script
VERSION = "2024-04-10_a"
BASE_IMAGE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/opaque"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/dz"
ZOOM_LEVELS = (-3, 3)
BASELINE_ZOOM = 2
UPPER_SQUARE_X = 66
LOWER_SQUARE_X = 16
UPPER_SQUARE_Y = 196
LOWER_SQUARE_Y = 19
SQUARE_PIXEL_LENGTH = 256
MULTIPROCESS_ENABLE = False
BACKGROUND_THRESHOLD = 0
BACKGROUND_COLOR = [0,0,0]

def rescaleImage(image, zoomLevel, scaleFactor):
	# Set the interpolation style
	kernelStyle = pv.enums.Kernel.LINEAR if zoomLevel < BASELINE_ZOOM else pv.enums.Kernel.NEAREST

	# Scale and write out the image
	zoomedImage = image.resize(scaleFactor, kernel=kernelStyle)
	return zoomedImage

def dz_padImage(image, offsetLeft_px, offsetBottom_px):
	"""
		Pads an image which is offset from (0,0) to include (0,0)
		- image: Image to be padded out
		- offsetLeft_px: Pixels between (0,0) and the image's left border
		- offsetBottom_px: Pixels between (0,0) and the image's bottom border
	"""
	bottomPadding = pv.Image.black(image.width, offsetBottom_px)
	image = image.join(bottomPadding, "vertical")
	leftPadding = pv.Image.black(offsetLeft_px, image.height)
	paddedImage = leftPadding.join(image, "horizontal")
	return paddedImage

def growImageToTileLayer(image, tileSize):
	"""
		Expands the right and top boundaries of the image such that:
			image.height % tileSize = 0
		This means the image can be cleanly divided at a certain zoom level
		- image: The image to be expanded
		- tileSize: The pixel dimensions of square tiles in this layer
	"""
	# Calculate how much of the horizontal direction is missing
	existingTile = (image.width % tileSize) / tileSize
	if existingTile != 0:
		# If the tile is incomplete creating padding equivalent to the missing amount
		missing_px = (1 - existingTile) * tileSize
		padding = pv.Image.black(missing_px, image.height)
		image = image.join(padding, "horizontal")

	# Calculate how much of the vertical direction is missing
	existingTile = (image.height % tileSize) / tileSize
	if existingTile != 0:
		# If the tile is incomplete creating padding equivalent to the missing amount
		missing_px = (1 - existingTile) * tileSize
		padding = pv.Image.black(image.width, missing_px)
		image = padding.join(image, "vertical")
	return image

def createTiles(imagePath):
	# Load the image
	fileName = os.path.splitext(os.path.basename(imagePath))[0]
	_, plane = fileName.split("_") # expecting plane_{plane}.png
	planeImage = pv.Image.new_from_file(imagePath)

	# Jagex uses an origin in the bottom left
	# The old script is slicing using (0, 0) bottom left
	# Dzsave can only assume an origin in the top right
	# This causes a vertical misalignment when the image height does not map onto the old method
	# To solve this, pad the images until they will exactly align at each zoom level
	fullImage = dz_padImage(planeImage, LOWER_SQUARE_X*SQUARE_PIXEL_LENGTH, LOWER_SQUARE_Y*SQUARE_PIXEL_LENGTH)

	for zoomLevel in range(ZOOM_LEVELS[0], ZOOM_LEVELS[1]+1):
		# Otherwise calculate the scalefactor
		scaleFactor = 2.0**zoomLevel / 2.0**BASELINE_ZOOM # zoomlevel 2 is the baseline
		zoomedImage = rescaleImage(fullImage, zoomLevel, scaleFactor)
		
		# Making dzsave align with (0,0) bottom left coordinates at all zoom levels
		# The size of tiles at each zoom level is fixed as a ratio to the baseline zoom tile size
		# For dzsave to align well there must be an integer number of tiles at each zoom level in both dimensions
		# Insert black padding to make this the case, dzsave will discard the empty tiles with background=0
		zoomedImage = growImageToTileLayer(zoomedImage, SQUARE_PIXEL_LENGTH)

		# Now slice it up into pyramidal layers
		zoomedImage.dzsave(os.path.join(OUTPUT_PATH, f"plane_{plane}/{zoomLevel}"), 
							tile_size=SQUARE_PIXEL_LENGTH, 
							suffix='.png[Q=100]', 
							depth='one', 
							overlap=0,
							layout='google', 
							region_shrink='nearest',
							background=BACKGROUND_COLOR,
							skip_blanks=BACKGROUND_THRESHOLD)

def createTiles_byplane():
	# Identify images
	fileType = "/*.png"
	imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{BASE_IMAGE_PATH}{fileType}")]

	if MULTIPROCESS_ENABLE:
		with multiprocessing.Pool() as pool:
			pool.map(createTiles, imageFilePaths)
	else:
		for imagePath in imageFilePaths:
			createTiles(imagePath)

if __name__ == "__main__":
	startTime = time.time()
	# createTiles_byplane()
	print(f"Peak memory usage: {max(memory_usage(proc=createTiles_byplane))}")
	print(f"Runtime: {time.time()-startTime}")