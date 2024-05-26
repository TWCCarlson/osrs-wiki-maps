### Coerces the file structure produced by the slicer to match the original
import os
import numpy as np
import time
import glob
import multiprocessing
from memory_profiler import memory_usage

VERSION = "2024-04-10_a"
PLANES_DIRECTORY = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/dz"
OUTPUT_DIRECTORY = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/dz"
PYRAMID_LAYOUT = "google"
MULTIPROCESS_ENABLE = False
UPPER_SQUARE_X = 66
LOWER_SQUARE_X = 16
UPPER_SQUARE_Y = 196
LOWER_SQUARE_Y = 19
BASELINE_ZOOM = 2

def restructureDirectories():
	if not os.path.exists(PLANES_DIRECTORY):
		raise FileNotFoundError("Base plane image directories not found")
	# Recursively grab all the files in the dzsave target directory
	planeDirectories = [os.path.normpath(path) for path in glob.glob(os.path.join(PLANES_DIRECTORY, "*/"))]

	# Restructure on a plane by plane basis
	if MULTIPROCESS_ENABLE:
		with multiprocessing.Pool() as pool:
			pool.starmap(restructureDirectory, (planeDirectories, PYRAMID_LAYOUT))
	else:
		for directory in planeDirectories:
			restructureDirectory(directory, PYRAMID_LAYOUT)

def restructureDirectory(directory, layout):
	# Generate an iterable of all the files in this pyramid directory
	pyramidSearchPath = os.path.join(directory, "**/*.png")
	pyramidFiles = glob.iglob(pyramidSearchPath, recursive=True)

	# Iterate
	for imagePath in pyramidFiles:
		# Google structure inserts images used to compare and eliminate empty tiles
		if os.path.split(imagePath)[-1] == "blank.png":
			continue
		renameFile(imagePath, layout)

def renameFile(imagePath, layout):
	# print(imagePath)
	if layout == "google":
		# Retrieve the slice data
		splitPath = os.path.normpath(imagePath).split(os.sep)[-5:]
		z = int(splitPath[0].split("_")[-1])
		zoom = int(splitPath[1])
		y = int(splitPath[-2])
		x = int(splitPath[-1].split(".")[0])
		# Transform to (0,0) bottom left coordinates for squares
		# X coordinate is already matching
		# Recall that the top and right bounds are integer tile based
		# This means the same math used to fill the tiles needs to be done again

		# Get the px height of the base image at this zoom level
		scaleFactor = 2.0**zoom / 2.0**BASELINE_ZOOM
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
		outputPath = os.path.join(OUTPUT_DIRECTORY, f"{zoom}")
		if not os.path.exists(outputPath):
			os.makedirs(outputPath)
		os.rename(imagePath, os.path.join(outputPath, f"{z}_{x}_{y}.png"))

if __name__ == "__main__":
	startTime = time.time()
	# restructureDirectories()
	print(f"Peak memory usage: {max(memory_usage(proc=restructureDirectories))}")
	print(f"Runtime: {time.time()-startTime}")