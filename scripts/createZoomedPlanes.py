### Scale images produced by the stitching script to different zoom levels
import glob
import os.path
import json

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv


def writeFile(outPath, image, zoomLevel, plane):
	outputDir = os.path.join(outPath, f"plane_{plane}")
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
	image.write_to_file(os.path.join(outputDir, f"{zoomLevel}.png"))


def rescalePlanes(sourcePath, outPath, zoomLevels, baselineZoomLevel, kernels):
	# Find the images that need to be rescaled
	fileType = "/*.png"
	imageFilePaths = [os.path.normpath(path) for path in glob.glob(f"{sourcePath}{fileType}")]

	for imagePath in imageFilePaths:
		rescalePlane(imagePath, outPath, zoomLevels, baselineZoomLevel, kernels)


def rescalePlane(imagePath, outPath, zoomLevels, baselineZoomLevel, kernels):
	# Load the image
	fileName = os.path.splitext(os.path.basename(imagePath))[0]
	_, plane = fileName.split("_") # expecting plane_{plane}.png
	inputImage = pv.Image.new_from_file(imagePath)
	
	for zoomLevel in range(zoomLevels["min"], zoomLevels["max"]+1):
		# Zoom level 2 is the baseline, so just write the image out
		if zoomLevel == baselineZoomLevel:
			writeFile(outPath, inputImage, zoomLevel, plane)
			
		# Otherwise calculate the scalefactor
		scaleFactor = 2.0**zoomLevel / 2.0**baselineZoomLevel # zoomlevel 2 is the baseline

		# Set the interpolation style
		kernelStyle = kernels[str(zoomLevel)]

		# Scale and write out the image
		zoomedImage = inputImage.resize(scaleFactor, kernel=kernelStyle)
		writeFile(outPath, zoomedImage, zoomLevel, plane)
		

def actionRoutine(basePath):
	"""
		Creates the various zoom levels used in the Leaflet map
		As of 5/30/24 the zoom level ranges from -3 to 3, with 2 being the base zoom
		Different kernels are used at different zoom levels:
		
		Nearest Neighbor is effective when upscaling
		Linear is used when downscaling
	"""
	# Use default values found in mapBuilderConfig.py
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configOpts = json.load(configFile)["ZOOM_OPTS"]

	zoomLevels = configOpts["zoomLevels"]
	baselineZoomLevel = configOpts["baselineZoomLevel"]
	kernels = configOpts["kernels"]
	sourcePath = configOpts["sourcePath"]
	outPath = configOpts["outPath"]

	sourcePath = os.path.join(basePath, sourcePath)
	outPath = os.path.join(basePath, outPath)
	if not os.path.exists(outPath):
		os.makedirs(outPath)

	rescalePlanes(sourcePath, outPath, zoomLevels, baselineZoomLevel, kernels)