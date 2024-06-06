### Paste icon images in their locations, on each zoom level
import glob
import os
import json
from PIL import Image
Image.MAX_IMAGE_PIXELS = 100000000000
from collections import defaultdict
import time

def writeFile(image, outPath, zoomLevel, plane):
	print(f"Writing: {os.path.join(outPath, f"{plane}/{zoomLevel}.png")}")
	outputDir = os.path.normpath(os.path.join(outPath, f"plane_{plane}"))
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
	image = image.convert("RGB")
	image.save(os.path.join(outputDir, f"{zoomLevel}.png"))


def implantIcons(planePath, iconPath, iconDefs, outPath, baselineZoom, zoomLevelHasIcons, coordinateData):
	# Process the icon data into per plane data sets
	iconLocations = defaultdict(list)
	with open(iconDefs) as iconJsonFile:
		iconJson = json.load(iconJsonFile)
		for iconData in iconJson:
			iconXPosition = int(iconData["position"]["x"])
			iconYPosition = int(iconData["position"]["y"])
			iconPlane = int(iconData["position"]["z"])
			iconSpriteID = int(iconData["spriteId"])
			iconLocations[iconPlane].append((iconXPosition, iconYPosition, iconSpriteID))

	# Load all the sprites
	fileType = "/*.png"
	spriteFilePaths = [os.path.normpath(path) for path in glob.glob(f"{iconPath}{fileType}")]
	spriteImages = defaultdict(str)
	for spriteFilePath in spriteFilePaths:
		spriteID = int(os.path.splitext(os.path.basename(spriteFilePath))[0])
		spriteImage = Image.open(spriteFilePath)
		spriteImages[spriteID] = spriteImage
	
	# Determine which zoom levels have icons
	zoomLevelsWithIcons = [int(level) for level in zoomLevelHasIcons if zoomLevelHasIcons[level] == True]

	# Paste sprites into their respective plane images
	fileType = "/*/"
	planeDirs = [os.path.normpath(path) for path in glob.glob(f"{planePath}{fileType}")]
	for plane in range(1, len(planeDirs)):
		for zoomLevel in zoomLevelsWithIcons:
			# Load image and add alpha channel for compositing
			planeImage = Image.open(os.path.join(planeDirs[plane], f"{zoomLevel}.png"))
			planeImage = planeImage.convert("RGBA")

			# Scale factor used in coordinate transforms for this zoom level
			scaleFactor = 2.0**zoomLevel / 2.0**baselineZoom

			# Draw the icons
			for iconData in iconLocations[plane]:
				planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData)
			writeFile(planeImage, outPath, zoomLevel, plane)

	# Plane 0 is intended to have ALL icons regardless of their assigned plane in the .json
	for zoomLevel in zoomLevelsWithIcons:
		# Load image and add alpha channel for compositing
		planeImage = Image.open(os.path.join(planeDirs[0], f"{zoomLevel}.png"))
		planeImage = planeImage.convert("RGBA")

		# Scale factor used in coordinate transforms for this zoom level
		scaleFactor = 2.0**zoomLevel / 2.0**baselineZoom

		# The apparent sorting order in the current wiki maps is 0 on top
		for iconData in iconLocations[1]:
			planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData)
		for iconData in iconLocations[2]:
			planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData)
		for iconData in iconLocations[3]:
			planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData)
		for iconData in iconLocations[0]:
			planeImage = drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData)
		writeFile(planeImage, outPath, zoomLevel, 0)


def drawIcon(planeImage, iconData, scaleFactor, spriteImages, coordinateData):
	iconXPos, iconYPos, iconSpriteID = iconData
	iconImage = spriteImages[iconSpriteID]

	# Load the information necessary for coordinate transform
	tileLength_px = coordinateData["tilePixelLength"]
	squareLength_tile = coordinateData["squareTileLength"]
	lowerSquareX = coordinateData["minSquareX"]
	lowerSquareY = coordinateData["minSquareY"]

	# Transform from Jagex bottom left to image bottom left (tiles)
	iconXPos = iconXPos - (lowerSquareX * squareLength_tile)
	iconYPos = iconYPos - (lowerSquareY * squareLength_tile)

	# Transform from image bottom left to image top left coordinates (pixels)
	# iconXPos_px = int(iconXPos * tileLength_px)
	# iconYPos_px = int(planeImage.height - (iconYPos * tileLength_px) - tileLength_px)

	# Adjust to correct image scale
	# iconXPos_px = iconXPos_px * scaleFactor
	# iconYPos_px = iconYPos_px * scaleFactor

	# Offset the icon to center it on the target tile
	# iconXPos_px = int(iconXPos_px - math.ceil(iconImage.width/2))
	# iconYPos_px = int(iconYPos_px - math.ceil(iconImage.height/2))
	iconXPosPX = int(iconXPos * tileLength_px * scaleFactor - iconImage.width/2 - (1 * scaleFactor))
	iconYPosPX = int((planeImage.height) - (iconYPos * tileLength_px * scaleFactor) - (tileLength_px * scaleFactor) - iconImage.height/2 + (3 * scaleFactor)) #+3 because of the origin change and tile pixel length=4
	
	# Paste the image in
	# planeImage.alpha_composite(iconImage, (iconXPos_px, iconYPos_px))
	# planeImage.alpha_composite(iconImage, (iconXPosPX, iconYPosPX))
	planeImage.paste(iconImage, (iconXPosPX, iconYPosPX), iconImage)
	return planeImage


def actionRoutine(basePath):
	"""
		Inserts map icons onto the plane images
		Unfortunately, pyvips is very slow at doing this and also limited by C stack
		This necessitates saving the images and loading from disk to do the operataion in memory
		PIL seems fastest at doing so out of openCV, pyvips, and PIL
		Could be worth looking into PIL-simd
	"""
	# Use default values found in mapBuilderConfig.py
	with open("./scripts/mapBuilderConfig.json") as configFile:
		config = json.load(configFile)
		configOpts = config["ICON_OPTS"]
		baselineZoom = config["ZOOM_OPTS"]["baselineZoomLevel"]

	planePath = configOpts["planePath"]
	iconPath = configOpts["iconPath"]
	iconDefs = configOpts["iconDefs"]
	outPath = configOpts["outPath"]
	zoomLevelHasIcons = configOpts["zoomLevelHasIcons"]
	planePath = os.path.join(basePath, planePath)
	iconPath = os.path.join(basePath, iconPath)
	iconDefs = os.path.join(basePath, iconDefs)
	outPath = os.path.join(basePath, outPath)

	# This script transforms in-game coordinates to pixels using dumped coordinate data
	with open(os.path.join(basePath, "coordinateData.json")) as coordFile:
		coordinateData = json.load(coordFile)

	implantIcons(planePath, iconPath, iconDefs, outPath, baselineZoom, zoomLevelHasIcons, coordinateData)

if __name__ == "__main__":
	startTime = time.time()
	actionRoutine("./osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	print(f"Took {time.time() - startTime}")