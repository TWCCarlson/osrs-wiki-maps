### Change all .pngs in a directory from 24bit to 32bit depth by adding an alpha channel
# Useful for pasting operations involving those images in the future
import glob
import os
import numpy as np
import cv2
import time
from memory_profiler import memory_usage

VERSION = "2024-04-10_a"
TARGET_DIRECTORY = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/base"
OUTPUT_DIRECTORY = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}/tiles/alpha"

def writeFile(image, plane, x, y):
	if not os.path.exists(OUTPUT_DIRECTORY):
		os.makedirs(OUTPUT_DIRECTORY)
	cv2.imwrite(os.path.join(OUTPUT_DIRECTORY, f"{plane}_{x}_{y}.png"), image)

def addAlphaChannels():
    fileType = "/*.png"
    imagePaths = [os.path.normpath(path) for path in glob.glob(f"{TARGET_DIRECTORY}{fileType}")]
    width, height, _ = cv2.imread(imagePaths[0], cv2.IMREAD_UNCHANGED).shape
    alpha = np.full((height, width), 255, dtype=np.uint8)
    for imagePath in imagePaths:
        fileName = os.path.splitext(os.path.basename(imagePath))[0]
        plane, x, y = map(int, fileName.split("_")) # Expecting {plane}_{x}_{y}

        # Insert alpha channel and save
        image = cv2.imread(imagePath, cv2.IMREAD_UNCHANGED)
        image_alpha = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        cv2.insertChannel(alpha, image_alpha, 3)
        writeFile(image_alpha, plane, x, y)

if __name__ == "__main__":
    startTime = time.time()
	# addAlphaChannels()
    print(f"Peak memory usage: {max(memory_usage(proc=addAlphaChannels))}")
    print(f"Runtime: {time.time()-startTime}")