### Scale images produced by the stitching script to different zoom levels
import os.path
import json
from platform import system
import time

runnerOS = system()
if runnerOS == "Windows":
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


def rescalePlane(planeImage, planeNum, basePath):
	"""
		Creates the various zoom levels used in the Leaflet map
		As of 5/30/24 the zoom level ranges from -3 to 3, with 2 being the base zoom
		Different kernels are used at different zoom levels:
		"kernels": {
            "-3": "linear",
            "-2": "linear",
            "-1": "linear",
            "0": "linear",
            "1": "linear",
            "2": "nearest",
            "3": "nearest"
        },
		Nearest Neighbor is effective when upscaling
		Linear is used when downscaling with fair results
	"""
	# Use default values found in mapBuilderConfig.py
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configOpts = json.load(configFile)["ZOOM_OPTS"]

	zoomLevels = configOpts["zoomLevels"]
	baselineZoomLevel = configOpts["baselineZoomLevel"]
	kernels = configOpts["kernels"]
	outPath = configOpts["outPath"]
	outPath = os.path.join(basePath, outPath)
	
	for zoomLevel in range(zoomLevels["min"], zoomLevels["max"]+1):
		timeStart = time.time()
		# Zoom level 2 is the baseline, so just write the image out
		if zoomLevel == baselineZoomLevel:
			writeFile(outPath, planeImage, zoomLevel, planeNum)
			continue
			
		# Otherwise calculate the scalefactor
		scaleFactor = 2.0**zoomLevel / 2.0**baselineZoomLevel # zoomlevel 2 is the baseline

		# Set the interpolation style (json keys can only be strings)
		kernelStyle = kernels[str(zoomLevel)]

		# Scale and write out the image
		zoomedImage = planeImage.resize(scaleFactor, kernel=kernelStyle)
		writeFile(outPath, zoomedImage, zoomLevel, planeNum)
		print(f"Rescaling {planeNum}@{zoomLevel} took {time.time() - timeStart}")