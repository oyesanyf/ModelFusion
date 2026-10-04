# Runner for build 333/334 merge
import os
import subprocess
import sys

script = os.path.join(os.path.dirname(__file__), "merge_build_334_pr.py")
subprocess.run([sys.executable, script], check=True)
