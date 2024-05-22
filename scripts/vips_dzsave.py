### Create a deepzoom pyramid from the full plane images
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
BASE_IMAGE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/opaque"
OUTPUT_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/dz"
ZOOM_LEVELS = (-3, 3)
BASELINE_ZOOM = 2

def rescaleImage(image, zoomLevel):
	# Otherwise calculate the scalefactor
	scaleFactor = 2.0**zoomLevel / 2.0**BASELINE_ZOOM # zoomlevel 2 is the baseline

	# Set the interpolation style
	kernelStyle = pv.enums.Kernel.LINEAR if zoomLevel < BASELINE_ZOOM else pv.enums.Kernel.NEAREST

	# Scale and write out the image
	zoomedImage = image.resize(scaleFactor, kernel=kernelStyle)
	return zoomedImage

def createTiles_onetile():
	# Identify images
	fileType = "/*.png"
	imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{BASE_IMAGE_PATH}{fileType}")]

	for imagePath in imageFilePaths:
		# Load the image
		fileName = os.path.splitext(os.path.basename(imagePath))[0]
		_, plane = fileName.split("_") # expecting plane_{plane}.png
		planeImage = pv.Image.new_from_file(imagePath)

		# Creating and slicing the downscaled versions
		zoomedImage = rescaleImage(planeImage, ZOOM_LEVELS[1])
		# Then slice
		zoomedImage.dzsave(os.path.join(OUTPUT_PATH, f"plane_{plane}"),
					 		tile_size=256, suffix='.png[Q=100]', 
							depth='onetile', 
							overlap=0, 
							layout='google', 
							region_shrink='nearest',
							background=0, 
							skip_blanks=0)
		
def createTiles_byplane():
	# Identify images
	fileType = "/*.png"
	imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{BASE_IMAGE_PATH}{fileType}")]

	for imagePath in imageFilePaths:
		# Load the image
		fileName = os.path.splitext(os.path.basename(imagePath))[0]
		_, plane = fileName.split("_") # expecting plane_{plane}.png
		planeImage = pv.Image.new_from_file(imagePath)

		for zoomLevel in range(ZOOM_LEVELS[0], ZOOM_LEVELS[1]+1):
			zoomedImage = rescaleImage(planeImage, zoomLevel)
			zoomedImage.dzsave(os.path.join(OUTPUT_PATH, f"plane_{plane}/{zoomLevel}"), 
					  			tile_size=256, 
					  			suffix='.png[Q=100]', 
								depth='one', 
								overlap=0,
								layout='google', 
								region_shrink='nearest',
								background=0,
								skip_blanks=0)
			
def debug():
	blank = pv.Image.new_from_file(os.path.join(OUTPUT_PATH, "plane_0/2/blank.png"))
	print(blank)
	tile = pv.Image.new_from_file(os.path.join(OUTPUT_PATH, "plane_0/2/0/106/42.png"))
	print(tile)

if __name__ == "__main__":
	startTime = time.time()
	# createTiles()
	# debug()
	print(f"Peak memory usage: {max(memory_usage(proc=createTiles_byplane))}")
	print(f"Runtime: {time.time()-startTime}")