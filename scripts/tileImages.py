### Create a deepzoom pyramid from the full plane images
import glob
import os
import time
from memory_profiler import memory_usage
import multiprocessing
import json
from collections import defaultdict

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv


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
	# This may be overexpanding
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


def createTiles(imagePath, outPath, coordinateData, baselineZoomLevel, backgroundColor, backgroundThreshold):
	# Load the image and its descriptive data
	# Expects /plane_{plane}/{zoomLevel}.png
	zoomLevel = os.path.splitext(os.path.basename(imagePath))[0]
	_, planeID = os.path.basename(os.path.dirname(imagePath)).split("_")
	planeImage = pv.Image.new_from_file(imagePath) # We no longer care about the alpha channel

	# Load coordinate data
	LOWER_SQUARE_X = coordinateData["minSquareX"]
	LOWER_SQUARE_Y = coordinateData["minSquareY"]
	SQUARE_PIXEL_LENGTH = coordinateData["squarePixelLength"]
	scaleFactor = 2.0**int(zoomLevel) / 2.0**baselineZoomLevel

	# Jagex uses an origin in the bottom left
	# The old script is slicing using (0, 0) bottom left
	# Dzsave can only assume an origin in the top right
	# This causes a vertical misalignment when the image height does not map onto the game coordinates well
	# To solve this, pad the images until they will exactly align at each zoom level
	missingX = LOWER_SQUARE_X * SQUARE_PIXEL_LENGTH * scaleFactor
	missingY = LOWER_SQUARE_Y * SQUARE_PIXEL_LENGTH * scaleFactor
	fullImage = dz_padImage(planeImage, missingX, missingY)
	
	# Making dzsave align with (0,0) bottom left coordinates at all zoom levels
	# The size of tiles at each zoom level is fixed as a ratio to the baseline zoom tile size
	# For dzsave to align well there must be an integer number of tiles at each zoom level in both dimensions
	# Insert black padding to make this the case, dzsave will discard the empty tiles with background=0
	zoomedImage = growImageToTileLayer(fullImage, SQUARE_PIXEL_LENGTH)

	# Now slice it up into tiles
	# Region shrink is a mandatory argument but is irrelevant because we are only slicing one zoom level
	# Google layout seems to produce the fewest extra files with no loss in speed
	zoomedImage.dzsave(os.path.join(outPath, f"plane_{planeID}/{zoomLevel}"), 
						tile_size=SQUARE_PIXEL_LENGTH, 
						suffix='.png[Q=100]', 
						depth='one',
						overlap=0,
						layout='google', 
						region_shrink='nearest',
						background=backgroundColor,
						skip_blanks=backgroundThreshold)


def createTiles_byplane(imagePath, outPath, coordinateData, baselineZoomLevel, backgroundColor, backgroundThreshold):
	# Identify images
	# Only some of the images may have icons per the passed in dict
	imageFilePaths = glob.glob(os.path.join(imagePath, f"**/*.png"))

	# Vips is very memory/cpu efficient for dzsave, and the files are small
	for imagePath in imageFilePaths:
		createTiles(imagePath, outPath, coordinateData, baselineZoomLevel, backgroundColor, backgroundThreshold)


def actionRoutine(basePath=None):
	"""
		Executes a dzsave operation on one layer at a time
		The result is a directory of sliced tiles using the scheme of the layout variable
	"""
	with open("./scripts/mapBuilderConfig.json") as configFile:
		config = json.load(configFile)
		configOpts = config["TILER_OPTS"]

	# This script needs boundary and transform data to ensure slicer alignment
	with open(os.path.join(basePath, "coordinateData.json")) as coordFile:
		coordinateData = json.load(coordFile)
		
	layerPath = configOpts["layerPath"]
	outPath = configOpts["outPath"]
	baselineZoomLevel = configOpts["baselineZoomLevel"]
	backgroundColor = configOpts["backgroundColor"]
	backgroundThreshold = configOpts["backgroundThreshold"]
	imagePath = configOpts["imagePath"]

	layerPath = os.path.join(basePath, layerPath)
	outPath = os.path.join(basePath, outPath)
	imagePath = os.path.join(basePath, imagePath)

	createTiles_byplane(imagePath, outPath, coordinateData, baselineZoomLevel, backgroundColor, backgroundThreshold)

if __name__ == "__main__":
	startTime = time.time()
	# createTiles_byplane()
	actionRoutine("./osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	# print(f"Peak memory usage: {max(memory_usage(proc=createTiles_byplane))}")
	print(f"Runtime: {time.time()-startTime}")