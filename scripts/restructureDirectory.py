### Coerces the file structure produced by the slicer to match the original
import os
import numpy as np
import time
import glob
import multiprocessing
from memory_profiler import memory_usage
import json
import shutil

def removeSubdirectories(topLevelDir):
	# Use DFS to find tree leaves and remove them
	dirsToRemove = [os.path.normpath(path) for path in glob.glob(os.path.join(topLevelDir, "**/"))]
	filesToRemove = [os.path.normpath(path) for path in glob.glob(os.path.join(topLevelDir, "*.*"))]
	# Traverse deeper into the tree
	for dir in dirsToRemove:
		# Empty subdirs and delete
		removeSubdirectories(dir)
		os.rmdir(dir)
	# Remove files
	for file in filesToRemove:
		os.remove(file)

def restructureDirectories(dzPath, outPath, coordinateData, baselineZoomLevel, multiprocessingEnabled):
	# Grab the parent plane directory locations
	planeDirectories = [os.path.normpath(path) for path in glob.glob(os.path.join(dzPath, "*/"))]

	# Restructure on a plane by plane basis
	if multiprocessingEnabled:
		# Bundle with args for starmapping
		# Pre-create directories when doing this, to avoid collisions
		argList = list()
		for planeDir in planeDirectories:
			argList.append((planeDir, outPath, coordinateData, baselineZoomLevel))
			for path in glob.glob(os.path.join(planeDir, "**/")):
				zoomLevel = os.path.basename(os.path.dirname(path))
				zoomLevelPath = os.path.join(outPath, zoomLevel)
				if not os.path.exists(zoomLevelPath):
					os.makedirs(zoomLevelPath)
		# Assign cores to plane directories
		# with multiprocessing.Pool() as pool:
		# 	pool.starmap(restructureDirectory, argList)
	else:
		for directory in planeDirectories:
			restructureDirectory(directory, outPath, coordinateData, baselineZoomLevel)
	
	removeSubdirectories(dzPath)
	os.rmdir(dzPath)

def restructureDirectory(directory, outPath, coordinateData, baselineZoomLevel,
						 xOffset=0):
	# Generate an iterable of all the files in this pyramid directory and subdirectories
	pyramidSearchPath = os.path.join(directory, "**/*.png")
	pyramidFiles = glob.iglob(pyramidSearchPath, recursive=True)

	# Iterate
	for imagePath in pyramidFiles:
		# Google structure inserts images used to compare and eliminate empty tiles, ignore
		if os.path.split(imagePath)[-1] == "blank.png":
			continue
		renameFile(imagePath, outPath, coordinateData, baselineZoomLevel, xOffset)


def renameFile(imagePath, outPath, coordinateData, baselineZoomLevel,
			   xOffset=0):
	# Retrieve the tile's location data
	splitPath = os.path.normpath(imagePath).split(os.sep)[-5:]
	planeNum = int(splitPath[0].split("_")[-1])
	zoom = int(splitPath[1])
	y = int(splitPath[-2])
	x = int(splitPath[-1].split(".")[0]) + xOffset
	# Transform to (0,0) bottom left coordinates for squares
	# X coordinate is already matching
	# Recall that the top and right bounds are integer tile based
	# This means the same math used to fill the layers needs to be done again here
	UPPER_SQUARE_Y = coordinateData["maxSquareY"]

	# Get the px height of the base image at this zoom level
	scaleFactor = 2.0**zoom / 2.0**baselineZoomLevel
	imageHeight = (UPPER_SQUARE_Y + 1) * 256 * scaleFactor
	if imageHeight % 256 == 0:
		# If the image height in tiles is an integer, then the size has been found
		missingPx = 0
	else:
		# If not, then calculate how many pixels are missing to reach the next integer
		missingPx = 256 - (imageHeight % 256)
	# Then the proper image height is the sum
	layerHeight = (imageHeight + missingPx) / 256
	# And conversion from the top left to bottom left origin can be made
	y = int(layerHeight - y - 1)
	outputPath = os.path.join(outPath, f"{zoom}")
	if not os.path.exists(outputPath):
		os.makedirs(outputPath)
	os.rename(imagePath, os.path.join(outputPath, f"{planeNum}_{x}_{y}.png"))


def actionRoutine(basePath):
	"""
		pyvips' dzsave operation uses some specific output directory formats
		These are not the output formats we want to use, so we need to modify the directories
		dzsave: /plane_{planeNum}/{zoomLevel}/0/{dz_y}/{dz_x}.png
		osrs: /{zoomLevel}/{planeNum}_{x}_{y}
	"""
	# Transforming to Jagex coordinates requires the coordinate data
	with open("./scripts/mapBuilderConfig.json") as configFile:
		config = json.load(configFile)
		configOpts = config["DIR_OPTS"]

	# This script needs boundary and transform data to ensure slicer alignment
	with open(os.path.join(basePath, "coordinateData.json")) as coordFile:
		coordinateData = json.load(coordFile)
	
	multiprocessingEnabled = configOpts["multiprocessingEnabled"]
	dzPath = configOpts["dzPath"]
	outPath = configOpts["outPath"]
	baselineZoomLevel = configOpts["baselineZoomLevel"]

	dzPath = os.path.join(basePath, dzPath)
	outPath = os.path.join(basePath, outPath)

	restructureDirectories(dzPath, outPath, coordinateData, baselineZoomLevel, multiprocessingEnabled)


if __name__ == "__main__":
	startTime = time.time()
	# restructureDirectories()
	actionRoutine("./osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	# print(f"Peak memory usage: {max(memory_usage(proc=restructureDirectories))}")
	print(f"Runtime: {time.time()-startTime}")