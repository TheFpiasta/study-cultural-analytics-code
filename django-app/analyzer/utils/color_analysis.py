# analyzer/utils/color_analysis.py

from PIL import Image
import numpy as np

def get_average_color(image_path):
    """Calculates the average color of an image."""
    with Image.open(image_path) as img:
        img = img.convert('RGB')  # Ensure it's in RGB mode
        np_img = np.array(img)
        avg_color = np_img.mean(axis=(0, 1))  # Calculate mean along the height and width
        return avg_color.astype(int)
