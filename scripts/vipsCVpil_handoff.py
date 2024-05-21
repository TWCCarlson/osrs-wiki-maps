### Script for benchmarking the handing off of image data between processing libraries
# We know some operations are faster for certain libraries than others
# e.g. vips resizes images significantly faster than PIL or openCV
# We would like to leverage this fact if the time loss is not too major
# openCV uses numpy arrays natively
# PIL has .fromarray and numpy has .asarray
# vips has .fromarray and numpy has .asarray
import time
from PIL import Image as pImage
pImage.MAX_IMAGE_PIXELS = 100000000000
import numpy as np
import os
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = str(pow(2,40))
import cv2
import glob
import imagesize
from memory_profiler import memory_usage

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv
pv.voperation.cache_set_max_files(1)

VERSION = "2024-04-10_a"
IMAGE_DIR = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/scaledplanes/3/"
TEST_IMAGES = [os.path.normpath(path) for path in glob.glob(f"{IMAGE_DIR}*.png")]
OUTPUT_DIR = f"./scripts/transfer_test"

def loadWith_vips(imagePath):
	return np.asarray(pv.Image.new_from_file(imagePath, access="sequential"))

def loadWith_pil(imagePath):
	return np.asarray(pImage.open(imagePath))

def loadWith_cv(imagePath):
	return np.asarray(cv2.imread(imagePath, cv2.IMREAD_UNCHANGED))

def writeWith_vips(array, ID, folderName):
	image = pv.Image.new_from_array(array)
	image.write_to_file(os.path.join(OUTPUT_DIR, f"{folderName}/image_{ID}.png"))

def writeWith_pil(array, ID, folderName):
	image = pImage.fromarray(array)
	image.save(os.path.join(OUTPUT_DIR, f"{folderName}/image_{ID}.png"))

def writeWith_cv(array, ID, folderName):
	cv2.imwrite(os.path.join(OUTPUT_DIR, f"{folderName}/image_{ID}.png"), array)

def vips_to_pil(imdir, ID):
	array = loadWith_vips(imdir)
	writeWith_pil(array, ID, "vips_to_pil")

def pil_to_vips(imdir, ID):
	array = loadWith_pil(imdir)
	writeWith_vips(array, ID, "pil_to_vips")

def vips_to_cv(imdir, ID):
	array = loadWith_vips(imdir)
	writeWith_cv(array, ID, "vips_to_cv")

def cv_to_vips(imdir, ID):
	array = loadWith_cv(imdir)
	writeWith_vips(array, ID, "cv_to_vips")

def pil_to_cv(imdir, ID):
	array = loadWith_pil(imdir)
	writeWith_cv(array, ID, "pil_to_cv")

def cv_to_pil(imdir, ID):
	array = loadWith_cv(imdir)
	writeWith_pil(array, ID, "cv_to_pil")

def benchmark(func):
	image_ID = 0
	for image in TEST_IMAGES:
		func(image, image_ID)
		image_ID += 1

def benchmark_all():
	TEST_ORDER = [vips_to_pil, pil_to_vips, vips_to_cv, cv_to_vips, pil_to_cv, cv_to_pil]
	# TEST_ORDER = [vips_to_pil]
	for testFunc in TEST_ORDER:
		testFunc = [testFunc]
		if not os.path.exists(os.path.join(OUTPUT_DIR, f"{testFunc[0].__name__}")):
			os.makedirs(os.path.join(OUTPUT_DIR, f"{testFunc[0].__name__}"))
		print(f"=== TESTING: {testFunc[0].__name__} ===")
		startTime = time.time()
		print(f"Peak memory usage: {max(memory_usage(proc=(benchmark, testFunc,)))}")
		print(f"Runtime: {time.time()-startTime}")

if __name__ == "__main__":
	if not os.path.exists(OUTPUT_DIR):
		os.makedirs(OUTPUT_DIR)
	print("Benchmarking data transfer between image processors...")
	print(f"Executing on {len(TEST_IMAGES)} images...")
	for image in TEST_IMAGES:
		print(f"\t{image}:{imagesize.get(image)}")
	total_startTime = time.time()
	benchmark_all()
	print("BENCHMARK COMPLETE")
	print(f"Runtime: {time.time()-total_startTime}")