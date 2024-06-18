import glob
import os

# Pick target directory
dir = f"osrs-wiki-maps/out/mapgen/versions/2024-05-29_a/tiles/rendered/-1/0"

# Load the files from the directory
files = glob.iglob(os.path.join(dir, f"*.png"))

# Filter
for file in files:
    fname = os.path.basename(file).split(".")[0]
    if "-icon" in fname:
        os.remove(file)
    elif "-old" in fname:
        id = fname.split("-")[0]
        # Remove the file that replaced this one
        replacedFilePath = os.path.join(os.path.dirname(file), f"{id}.png")
        os.remove(replacedFilePath)
        # Rename the file back to the original
        os.rename(file, replacedFilePath)