### Overlay two images, creating a transparency out of the first
import glob
import os
import time
from memory_profiler import memory_usage
from collections import defaultdict
import math

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv

VERSION = "2024-04-10_a"
BASE_IMAGE_PATH = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/opaque"
OUTPUT_DIRECTORY = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/fullplanes/composites"
TRANSPARENCY_COLOR = 0
TRANSPARENCY_TOLERANCE = 0
PLANE_COUNT = 4
BLUR_RADIUS = 1
BRIGHTNESS_FRAC = 0.5 # centered on 1, values outside [0.0, 2.0] are clamped by RGB range, skip if 1
CONTRAST_FRAC = 0.8 # range: [0.0, 2.0], skip if 1
GRAYSCALE_FRAC = 0.9 # (0, 1.0], skip if 0

def createComposite(baseImage, superImage):
	pass

def styleLayer(layerImage):
		# Brightness and contrast
	brightnessValue = ((BRIGHTNESS_FRAC * 255) - 255) / 4
	# contrastValue = ((CONTRAST_FRAC * 255) - 255) / 2
	# contrastCorrection = (259 * (contrastValue + 255)) / (255 * (259 - contrastValue))
	layerImage = CONTRAST_FRAC * (layerImage - 127) + (127 + brightnessValue)

	# Grayscale
	if 0 < GRAYSCALE_FRAC <= 1:
		layerImage = (layerImage.colourspace("hsv") * [1, (1-GRAYSCALE_FRAC), 1]).colourspace("srgb")

	# Color Palette
	# Seems unpopular, but would be sepia, etc

	# Dropshadow
	# Seems unpopular, looks nice in some areas of the map

	# Blur
	# Preview the radius of this blur operation using:
	# print(pv.Image.gaussmat(sigma, min_ampl, precision="float", separable=True).rot90().numpy())
	# pyvips implementation skips the first term of the Gaussian: https://www.libvips.org/API/8.9/libvips-create.html#vips-gaussmat
	if BLUR_RADIUS > 0:
		sigma = 1
		n = BLUR_RADIUS + 1 
		nthGaussTerm = math.e ** ((-n**2)/(2 * (sigma**2)))
		layerImage = layerImage.gaussblur(sigma, min_ampl=nthGaussTerm, precision="float")

	return layerImage

def createComposites():
	# Locate plane images
	planeImagePaths = [os.path.normpath(path) for path in glob.glob(os.path.join(BASE_IMAGE_PATH, "*.png"))]

	# Load images, ensuring the right order
	planeDict = defaultdict(pv.Image)
	for planeImagePath in planeImagePaths:
		imageName = os.path.splitext(os.path.basename(planeImagePath))[0]
		planeNum = int(imageName.split("_")[-1])
		planeImage = pv.Image.new_from_file(planeImagePath)
		planeDict[planeNum] = planeImage
	
	# Initialize with the base plane
	baseImage = planeDict[0]

	# Stack the other layers on top of it
	for planeNum in range(0, PLANE_COUNT):
		# Style the underlay plane
		styledBaseImage = styleLayer(baseImage)
		if planeNum == 0:
			# There is nothing to overlay on the base plane
			continue

		# Get the overlay plane
		overlayImage = planeDict[planeNum]

		# Create a mask treating non-background pixels as 255 from the overlay
		mask = (abs(overlayImage - TRANSPARENCY_COLOR) > TRANSPARENCY_TOLERANCE).bandor()

		# Insert overlay pixels where the mask is true, and base pixels where false
		styledCompositeImage = mask.ifthenelse(overlayImage, styledBaseImage)
		styledCompositeImage.write_to_file(os.path.join(OUTPUT_DIRECTORY, f"plane_{planeNum}.png"))

		# Separately, merge the overlay with the not-styled underlay to become the underlay for the next plane
		baseImage = mask.ifthenelse(overlayImage, baseImage)

if __name__ == "__main__":
	startTime = time.time()
	# createComposite()
	print(f"Peak memory usage: {max(memory_usage(proc=createComposites))}")
	print(f"Runtime: {time.time()-startTime}")