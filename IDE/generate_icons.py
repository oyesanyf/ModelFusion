"""Convert the HugOS brain icon to ICO format with multiple sizes for Windows."""
from PIL import Image
import sys
import os

def create_ico(input_path, output_path, sizes=None):
    if sizes is None:
        sizes = [256, 128, 64, 48, 32, 16]
    
    img = Image.open(input_path).convert('RGBA')
    
    # Create resized versions
    icons = []
    for size in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        icons.append(resized)
    
    # Save as ICO
    icons[0].save(output_path, format='ICO', sizes=[(s, s) for s in sizes], append_images=icons[1:])
    print(f"Created {output_path} with sizes: {sizes}")
    print(f"File size: {os.path.getsize(output_path)} bytes")

def create_png(input_path, output_path, size):
    img = Image.open(input_path).convert('RGBA')
    resized = img.resize((size, size), Image.LANCZOS)
    resized.save(output_path, format='PNG')
    print(f"Created {output_path} ({size}x{size})")

if __name__ == '__main__':
    source = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    
    # Create ICO for Windows installer/shortcut
    create_ico(source, os.path.join(out_dir, 'hugos.ico'))
    
    # Create individual PNGs for various uses
    for size in [1024, 512, 256, 128, 64, 48, 32, 16]:
        create_png(source, os.path.join(out_dir, f'hugos_{size}x{size}.png'), size)
    
    print("\nAll icons generated successfully!")
