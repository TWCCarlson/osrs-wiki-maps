### Build a large image out of the region tiles produced by RuneLite's image dumper
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

# Collect plane images
fileType = "/*.png"
imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{BASE_IMAGE_PATH}{fileType}")]

def buildZoomLevels():
	for zoomLevel in range(ZOOM_LEVELS[0], ZOOM_LEVELS[1]+1):
		buildZoomLevel(zoomLevel)

def buildZoomLevel(zoomLevel):
	for imagePath in imageFilePaths:
		fileName = os.path.splitext(os.path.basename(imagePath))[0]
		_, plane = fileName.split("_") # expecting {plane}_{x}_{y}
		inputImage = pv.Image.new_from_file(imagePath)
		outputDir = os.path.join(OUTPUT_PATH, f"{zoomLevel}")

		# Zoom level 2 is the baseline, so just write the image out
		if zoomLevel == 2:
			if not os.path.exists(outputDir):
				os.makedirs(outputDir)
			inputImage.write_to_file(os.path.join(OUTPUT_PATH, f"{zoomLevel}/plane_{plane}.png"))

		# Otherwise calculate the scalefactor
		scaleFactor = 2.0**zoomLevel / 2.0**2 # zoomlevel 2 is the baseline

		# Set the interpolation style
		kernelStyle = pv.enums.Kernel.LINEAR if zoomLevel <= 1 else pv.enums.Kernel.NEAREST

		# Scale and write out the image
		zoomedImage = inputImage.resize(scaleFactor, kernel=kernelStyle)
		
		if not os.path.exists(outputDir):
			os.makedirs(outputDir)
		zoomedImage.write_to_file(os.path.join(outputDir, f"plane_{plane}.png"))

if __name__ == "__main__":
	startTime = time.time()
	# buildZoomLevels()
	print(f"Peak memory usage: {max(memory_usage(proc=buildZoomLevels))}")
	print(f"Runtime: {time.time()-startTime}")