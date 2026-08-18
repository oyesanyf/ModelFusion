import shutil
import os

target_dir = r"d:\harfile\ModelFusion\.agents\commands"
if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
    print(f"Deleted directory {target_dir}")
else:
    print("Directory does not exist.")
