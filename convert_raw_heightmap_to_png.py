from PIL import Image
import numpy as np

def convert_raw_heightmap_to_png(raw_file_path, output_png_path, width, height, bit_depth=16, byte_order='little'):
    print(f"\nConverting '{raw_file_path}' to '{output_png_file}'...")
    if bit_depth == 8:
        dtype = np.uint8
        pil_mode = 'L'
    elif bit_depth == 16:
        dtype = np.uint16
        pil_mode = 'I;16'

    with open(raw_file_path, 'rb') as f:
        raw_data = f.read()

    height_array = np.frombuffer(raw_data, dtype=dtype)

    expected_size = width * height
    if height_array.size != expected_size:
        raise ValueError(f"Raw file size mismatch. Expected {expected_size} pixels ({width}x{height}), but got {height_array.size} pixels.")

    if bit_depth == 16 and byte_order == 'big':
        height_array = height_array.byteswap()

    height_array = height_array.reshape((height, width))

    if bit_depth == 16:
        image = Image.fromarray(height_array, mode=pil_mode)
    else: # 8-bit
        image = Image.fromarray(height_array, mode=pil_mode)

    image.save(output_png_path)
    print(f"Successfully converted '{raw_file_path}' (W:{width}, H:{height}, D:{bit_depth}) to '{output_png_path}'")

if __name__ == "__main__":
    width = 512
    height = 512
    bit_depth = 16
    raw_file = '/home/ubuntu/Downloads/Terrain_heightmap.raw'
    output_png_file = '/home/ubuntu/Downloads/Terrain_heightmap.png'
    convert_raw_heightmap_to_png(raw_file, output_png_file, width, height, bit_depth, 'little')