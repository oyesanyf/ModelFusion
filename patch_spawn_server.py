import os
import glob
import re

def main():
    ide_dir = r"d:\harfile\ModelFusion\IDE\VSCode-win32-x64\resources\app"
    pattern = os.path.join(ide_dir, "extensions", "**", "dist", "extension.js")
    files = glob.glob(pattern, recursive=True)

    patched_count = 0
    for f in files:
        with open(f, 'r', encoding='utf8') as file:
            content = file.read()

        if "this._spawnPersistentServer()" in content:
            content = content.replace("this._spawnPersistentServer()", "this.startServer()")
            
            with open(f, 'w', encoding='utf8') as file:
                file.write(content)
            
            patched_count += 1
            print(f"Patched {f}")

    print(f"Successfully patched {patched_count} files.")

if __name__ == "__main__":
    main()
