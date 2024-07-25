import platform
import os

def initializePyvips():
    # Detects the OS, then dispatches the import as needed
    OPERATING_SYSTEM = platform.system()
    if OPERATING_SYSTEM == "Windows":
        # Windows binaries are required: 
        # https://pypi.org/project/pyvips/
        # https://www.libvips.org/install.html
        LIBVIPS_VERSION = "8.15"
        vipsbin = os.path.abspath(f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
        os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
        # os.environ['VIPS_PROFILE'] = "1"
        # os.environ["VIPS_CONCURRENCY"] = "1"
        # logging.basicConfig(level = logging.DEBUG)
    elif OPERATING_SYSTEM == "Linux":
        pass
    else:
        raise OSError("Operating system not recognized as Linux or Windows "
                    "for Pyvips Import")
    
initializePyvips()
import pyvips