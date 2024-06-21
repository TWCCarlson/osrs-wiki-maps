import glob
from collections import defaultdict
import time

import os.path
import cache
import createCompositeImages
import createZoomedPlanes
import drawMapIcons
import tileImages
import restructureDirectory
import insertIcons

# runnerOS = system()
# if runnerOS == "Windows":
# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

# fetchCache()
# fetchXTEA()
# dumpMapData()
# createCompositePlanes()
# rescalePlanes()
# generateBaseTiles()
# reshapeDirectory()
# for mapID in mapIDs
#     buildMapID()
#     drawIcons()
#     sliceImage()
#     reshapeDirectory()


if __name__ == "__main__":
	"""
		Build ALL maps used in the wiki from scratch
	"""
	startTime = time.time()
	# 1. Retrieve the latest cache files and XTEA keys
	# outputDir = cache.download(f"./osrs-wiki-maps/out/mapgen/versions")
	outputDir = os.path.join(f"./osrs-wiki-maps/out/mapgen/versions", "2024-05-29_a")

	# 2. Dump map data using RuneLite
	# Call the java program to dump map data
	# When this is working, the version of the cache and xteas will need to be passed in alongside the directory
	# It should build a directory inside /mapgen/versions/ called fullplanes and dump the images there
	# It should also return that directory
	# planeImageDir = somefunction()
	planeImageDir = os.path.join(outputDir, "fullplanes/base")

	# Record image paths by plane
	fileType = "/*.png"
	planeImagePaths = defaultdict(str)
	for imagePath in (os.path.normpath(path) for path in glob.glob(f"{planeImageDir}{fileType}")):
		imageName = os.path.splitext(os.path.basename(imagePath))[0]
		planeNum = int(imageName.split("_")[-1])
		planeImagePaths[planeNum] = imagePath

	# The following steps are done plane-by-plane
	for planeNum, planePath in planeImagePaths.items():
		# 3. Create the composite image of the plane
		# print(f"COMPOSITING {planeNum}")
		planeImage = createCompositeImages.createComposites(planeNum, planeImagePaths)
		# outPath = f"./osrs-wiki-maps/out/mapgen/versions/2024-05-29_a/fullplanes/composites/"
		# if not os.path.exists(outPath):
		# 	os.makedirs(outPath)
		# planeImage.write_to_file(os.path.join(outPath, f"plane_{planeNum}.png"))

		# 4. Rescale the plane and save
		print(f"RESCALING {planeNum}")
		createZoomedPlanes.rescalePlane(planeImage, planeNum, outputDir)
	print(f"Vips operations took: {time.time()-startTime}")

	# for planeNum, planePath in planeImagePaths.items():
		# planeImage = pv.Image.new_from_file(planePath)
		# createZoomedPlanes.rescalePlane(planeImage, planeNum, outputDir)

	# 5. Slice the rendered planes and rescale
	sliceTime = time.time()
	tileImages.actionRoutine(outputDir)
	print(f"Slicing took: {time.time()-sliceTime}")

	# 6. Restructure the directory to match what's expected
	dirTime = time.time()
	restructureDirectory.actionRoutine(outputDir, "-1")
	print(f"Directory fix took: {time.time()-dirTime}")

	# Draw icons onto tiles
	# iconTime = time.time()
	# insertIcons.actionRoutine(outputDir)
	# print(f"Icon insertion took: {time.time()-iconTime}")

	# Done
	print(f"Finished in {time.time()-startTime} seconds")