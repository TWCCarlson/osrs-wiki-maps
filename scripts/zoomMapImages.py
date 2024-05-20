### Scale images produced by the stitching script to different zoom levels
import glob
import os
import time
from memory_profiler import memory_usage

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

### Configure this before running the script
VERSION = "2024-04-10_a"
BASE_IMAGE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/scaledplanes"
ZOOM_LEVELS = (-3, 3)
BASELINE_ZOOM = 2

# Collect plane images
fileType = "/*.png"
imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{BASE_IMAGE_PATH}{fileType}")]

def writeFile(image, zoomLevel, plane):
	outputDir = os.path.join(OUTPUT_PATH, f"{zoomLevel}")
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
	image.write_to_file(os.path.join(outputDir, f"plane_{plane}.png"))

def rescalePlanes():
	for imagePath in imageFilePaths:
		rescalePlane(imagePath)

def rescalePlane(imagePath):
	# Load the image
	fileName = os.path.splitext(os.path.basename(imagePath))[0]
	_, plane = fileName.split("_") # expecting plane_{plane}.png
	inputImage = pv.Image.new_from_file(imagePath)
	
	for zoomLevel in range(ZOOM_LEVELS[0], ZOOM_LEVELS[1]+1):
		# Zoom level 2 is the baseline, so just write the image out
		if zoomLevel == BASELINE_ZOOM:
			writeFile(inputImage, zoomLevel, plane)
			
		# Otherwise calculate the scalefactor
		scaleFactor = 2.0**zoomLevel / 2.0**BASELINE_ZOOM # zoomlevel 2 is the baseline

		# Set the interpolation style
		kernelStyle = pv.enums.Kernel.LINEAR if zoomLevel <= 1 else pv.enums.Kernel.NEAREST

		# Scale and write out the image
		zoomedImage = inputImage.resize(scaleFactor, kernel=kernelStyle)
		writeFile(zoomedImage, zoomLevel, plane)

if __name__ == "__main__":
	# buildZoomLevels()
	startTime = time.time()
	# rescalePlanes()
	print(f"Peak memory usage: {max(memory_usage(proc=rescalePlanes))}")
	print(f"Runtime: {time.time()-startTime}")