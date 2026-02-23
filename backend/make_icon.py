import sys
from PIL import Image

def generate_icon(input_path, output_path):
    img = Image.open(input_path)
    # Convert to typical ICO sizes
    icon_sizes = [(16,16), (32, 32), (48, 48), (64,64), (128, 128), (256, 256)]
    img.save(output_path, format="ICO", sizes=icon_sizes)
    print("Icon generated successfully at", output_path)

if __name__ == "__main__":
    generate_icon(sys.argv[1], sys.argv[2])
