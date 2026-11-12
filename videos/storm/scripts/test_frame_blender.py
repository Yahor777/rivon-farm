"""Entry point for the Blender binary (blender -b -P test_frame_blender.py -- out w h spp shot): same as test_frame.py."""
import sys, runpy
from pathlib import Path
argv = sys.argv[sys.argv.index("--") + 1:]
sys.argv = [str(Path(__file__).with_name("test_frame.py"))] + argv
runpy.run_path(sys.argv[0], run_name="__main__")
