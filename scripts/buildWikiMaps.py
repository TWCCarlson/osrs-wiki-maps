import os.path
import cache
import restructureDirectory
import buildMapIDs
import sys
import json
import glob

BASE_DIRECTORY = "osrs-wiki-maps/out/mapgen/versions"

# runnerOS = system()
# if runnerOS == "Windows":
# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

def getCache(version=None):
	# Fetch the latest, or the version supplied as an argument, game cache
	cache.download(f"./osrs-wiki-maps/out/mapgen/versions", version)

def createBaseTiles(version):
	# Slice the cache dump result to produce the base tiles for game maps
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configData = json.load(configFile)
		backgroundColor = configData["TILER_OPTS"]["backgroundColor"]
		backgroundThreshold = configData["TILER_OPTS"]["backgroundThreshold"]
	with open("./osrs-wiki-maps/coordinateData.json") as coordFile:
		coordData = json.load(coordFile)

	# Find the base plane images
	baseDirectory = os.path.join(BASE_DIRECTORY, version)
	imageBasePath = os.path.join(baseDirectory, "fullplanes/base")
	imageFilePaths = glob.glob(os.path.join(imageBasePath, "**.*png"))
	dzSaveOutPath = os.path.join(baseDirectory, "tiles/dzSave")

	# Identify the bottom left coordinates
	LOWER_SQUARE_X = coordData["minSquareX"]

	# Slice each image
	for planeImagePath in imageFilePaths:
		# Identify the plane
		fileName = os.path.basename(planeImagePath)
		_, planeNum = os.path.splitext(fileName)[0].split("_")

		# Load the image and slice
		planeImage = pv.Image.new_from_file(planeImagePath)
		planeImage.dzsave(os.path.join(dzSaveOutPath, f"plane_{planeNum}/2"),
						  tile_size= 256,
						  suffix= '.png[Q=100]',
						  depth= 'one',
						  overlap= 0,
						  layout='google',
						  region_shrink='nearest',
						  background=backgroundColor,
						  skip_blanks=backgroundThreshold)
		
	# Restructure the output of the slicer to comport with Jagex coordinates
	targetDirectory = os.path.join(baseDirectory, "tiles/base")
	planeTileDirectories = glob.glob(os.path.join(dzSaveOutPath, "*/"))
	for directory in planeTileDirectories:
		restructureDirectory.restructureDirectory(directory, 
												  targetDirectory,
											  	  coordData, 2, 
												  xOffset=LOWER_SQUARE_X)
	restructureDirectory.removeSubdirectories(dzSaveOutPath)
	os.rmdir(dzSaveOutPath)

def buildAllMapIDs(version):
	baseDirectory = os.path.join(BASE_DIRECTORY, version)
	buildMapIDs.actionRoutine(baseDirectory)
	pass

if __name__ == "__main__":
	"""
	Main file containing the top-level functions to be called for generating
	map tiles for the OSRS wiki. The intended call order, automatable via
	GitHub Actions, is:

	1) getCache(optional version arg) -> working directory path
	2) Dump from the game cache(workingPath)
	3) createBaseTiles(workingPath)
	4) buildMapIDs(workingPath)
	"""
	args = sys.argv
	# args[0] = current file
	# args[1] = function name
	# args[2:] = function args : (*unpacked)
	globals()[args[1]](*args[2:])