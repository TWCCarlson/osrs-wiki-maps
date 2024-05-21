### Paste icon images in their locations, on each zoom level
import glob
import os
import json
from PIL import Image
Image.MAX_IMAGE_PIXELS = 100000000000
import numpy as np
import time
from collections import defaultdict
from memory_profiler import memory_usage

VERSION = "2024-04-10_a"
DEFINITIONS_FILE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/minimapIcons.json"
ICON_SPRITES_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/icons"
PLANE_FILE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/scaledplanes/"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/iconplanes"
PLANE_COUNT = 4
ZOOM_LEVELS_WITH_ICONS = (-3, 3)
BASELINE_ZOOM = 2
TILE_PIXEL_LENGTH = 4
SQUARE_TILE_LENGTH = 64
SQUARE_PIXEL_LENGTH = TILE_PIXEL_LENGTH * SQUARE_TILE_LENGTH
UPPER_SQUARE_X = 66
LOWER_SQUARE_X = 16
UPPER_SQUARE_Y = 196
LOWER_SQUARE_Y = 19
SPRITE_PIXEL_LENGTH = 15

# Remember there's a fencepost problem here, add one square length of pixels
planeWidth = (UPPER_SQUARE_X - LOWER_SQUARE_X + 1) * SQUARE_PIXEL_LENGTH
planeHeight = (UPPER_SQUARE_Y - LOWER_SQUARE_Y + 1) * SQUARE_PIXEL_LENGTH

# We aren't rendering tiles from (0,0), so find the offset giving the new origin
hOffset = (LOWER_SQUARE_X) * SQUARE_PIXEL_LENGTH
vOffset = (LOWER_SQUARE_Y) * SQUARE_PIXEL_LENGTH

def writeFile(image, zoomLevel, plane):
	outputDir = os.path.normpath(os.path.join(OUTPUT_PATH, f"{zoomLevel}"))
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
	image.save(os.path.join(outputDir, f"plane_{plane}.png"))

def implantIcons():
	# Process the icon data into per plane data sets
	iconLocations = defaultdict(list)
	with open(DEFINITIONS_FILE_PATH) as iconJsonFile:
		iconJson = json.load(iconJsonFile)
		for iconData in iconJson:
			iconXPosition = int(iconData["position"]["x"])
			iconYPosition = int(iconData["position"]["y"])
			iconPlane = int(iconData["position"]["z"])
			iconSpriteID = int(iconData["spriteId"])
			iconLocations[iconPlane].append((iconXPosition, iconYPosition, iconSpriteID))

	# Load all the sprites
	fileType = "/*.png"
	spriteFilePaths = [os.path.normpath(path) for path in glob.glob(f"{ICON_SPRITES_PATH}{fileType}")]
	spriteImages = defaultdict(str)
	for spriteFilePath in spriteFilePaths:
		spriteID = int(os.path.splitext(os.path.basename(spriteFilePath))[0])
		spriteImage = Image.open(spriteFilePath)
		spriteImages[spriteID] = spriteImage
	
	# Paste sprites into their respective plane images
	for plane in range(1, PLANE_COUNT):
		implantIconsByZoom(plane, iconLocations, spriteImages)

	# Plane 0 is intended to have ALL icons regardless of their level in the .json
	implantIconsByZoom(0, iconLocations, spriteImages, ALL_ICONS=True)
	
def implantIconsByZoom(plane, iconLocations, spriteImages, ALL_ICONS=False):
	for zoomLevel in range(ZOOM_LEVELS_WITH_ICONS[0], ZOOM_LEVELS_WITH_ICONS[1]+1):
		planeImage = Image.open(os.path.join(PLANE_FILE_PATH, f"{zoomLevel}/plane_{plane}.png"))

		# Scale factor used in coordinate transforms for this zoom level
		scaleFactor = 2.0**zoomLevel / 2.0**BASELINE_ZOOM

		# If requesting all icons be drawn to this plane
		if ALL_ICONS:
			planeImage = drawAllIcons(planeImage, iconLocations, scaleFactor, spriteImages)
		else:
			# Otherwise only draw spec'd icons
			for iconData in iconLocations[plane]:
				planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages)
		writeFile(planeImage, zoomLevel, plane)

def drawAllIcons(planeImage, iconLocations, scaleFactor, spriteImages):
	# Draw all icons to this image regardless of z spec
	for zSpec in range(PLANE_COUNT):
		for iconData in iconLocations[zSpec]:
			planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages)
	return planeImage

def drawIcon(planeImage, iconData, scaleFactor, spriteImages):
	iconXPos, iconYPos, iconSpriteID = iconData
	# Coordinate transform to render origin
	iconXPos = iconXPos - (LOWER_SQUARE_X * SQUARE_TILE_LENGTH)
	iconYPos = iconYPos - (LOWER_SQUARE_Y * SQUARE_TILE_LENGTH)

	# Coordinate transform to pixels
	iconXPosPX = int(iconXPos * TILE_PIXEL_LENGTH * scaleFactor - SPRITE_PIXEL_LENGTH/2 - (1 * scaleFactor))
	iconYPosPX = int((planeHeight * scaleFactor) - (iconYPos * TILE_PIXEL_LENGTH * scaleFactor) - (TILE_PIXEL_LENGTH * scaleFactor) - SPRITE_PIXEL_LENGTH/2 + (3 * scaleFactor)) #+3 because of the origin change and tile pixel length=4

	# Paste the image in
	planeImage.alpha_composite(spriteImages[iconSpriteID], (iconXPosPX, iconYPosPX))
	return planeImage

if __name__ == "__main__":
	startTime = time.time()
	# implantIcons()
	print(f"Peak memory usage: {max(memory_usage(proc=implantIcons))}")
	print(f"Runtime: {time.time()-startTime}")