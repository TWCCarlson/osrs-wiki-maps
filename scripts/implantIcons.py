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

# For the highest zoom level we are dealing with images exceeding the openCV default limit
# os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = str(pow(2,40))
# import cv2

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
	# cv2.imwrite(os.path.join(outputDir, f"plane_{plane}.png"), image)
	image.save(os.path.join(outputDir, f"plane_{plane}.png"))

def implantIcons():
	# Load the icon location definitions file 
	# Load the icons
	# Iterate through the definition file's data (z is plane)
	# The most memory-intensive part will be pasting in the zoom 3 planes
	# So maybe things should be separated by plane
	# For each zoom level, paste the icons into the fullplane images using numpy 

	# Process the icon data into per plane tuples
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
		# spriteImage = cv2.imread(spriteFilePath, cv2.IMREAD_UNCHANGED)
		spriteImage = Image.open(spriteFilePath)
		spriteImages[spriteID] = spriteImage
		# cv2.imshow("sprite", spriteImage)
		# cv2.waitKey(0)
	
	# Paste sprites into their respective plane images
	for plane in range(PLANE_COUNT):
		iconCount = 0
		for zoomLevel in range(ZOOM_LEVELS_WITH_ICONS[0], ZOOM_LEVELS_WITH_ICONS[1]+1):
			# planeImage = cv2.imread(os.path.join(PLANE_FILE_PATH, f"{zoomLevel}/plane_{plane}.png"), cv2.IMREAD_UNCHANGED)
			planeImage = Image.open(os.path.join(PLANE_FILE_PATH, f"{zoomLevel}/plane_{plane}.png"))

			# Scale factor used in coordinate transforms for this zoom level
			scaleFactor = 2.0**zoomLevel / 2.0**BASELINE_ZOOM

			# Iterate over all the icons in this plane
			for iconData in iconLocations[plane]:
				iconXPos, iconYPos, iconSpriteID = iconData
				# Coordinate transform to render origin
				iconXPos = iconXPos - (LOWER_SQUARE_X * SQUARE_TILE_LENGTH)
				iconYPos = iconYPos - (LOWER_SQUARE_Y * SQUARE_TILE_LENGTH)

				# Coordinate transform to pixels
				iconXPosPX = int(iconXPos * TILE_PIXEL_LENGTH * scaleFactor - SPRITE_PIXEL_LENGTH/2 + 2)
				iconYPosPX = int((planeHeight * scaleFactor) - (iconYPos * TILE_PIXEL_LENGTH * scaleFactor) - (TILE_PIXEL_LENGTH * scaleFactor) - SPRITE_PIXEL_LENGTH/2 + 2)

				# Paste the image in
				# planeImage[iconYPosPX:iconYPosPX+SPRITE_PIXEL_LENGTH, iconXPosPX:iconXPosPX+SPRITE_PIXEL_LENGTH] = spriteImages[iconSpriteID]
				# planeImage.composite(spriteImages[iconSpriteID], mode=pv.enums.BlendMode.OVER, x=iconXPosPX, y=iconYPosPX)
				# planeImage.paste(spriteImages[iconSpriteID], (iconXPosPX, iconYPosPX), spriteImages[iconSpriteID])
				planeImage.alpha_composite(spriteImages[iconSpriteID], (iconXPosPX, iconYPosPX))
				# cv2.rectangle(planeImage, (iconXPosPX, iconYPosPX), (iconXPosPX+SPRITE_PIXEL_LENGTH, iconYPosPX+SPRITE_PIXEL_LENGTH), (0,0,255), 1)
			
			writeFile(planeImage, zoomLevel, plane)

if __name__ == "__main__":
	startTime = time.time()
	# implantIcons()
	print(f"Peak memory usage: {max(memory_usage(proc=implantIcons))}")
	print(f"Runtime: {time.time()-startTime}")