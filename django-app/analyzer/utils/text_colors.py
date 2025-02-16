from PIL import Image
import numpy as np
from collections import Counter

def get_dominant_color(image):
    """Returns the most common (dominant) color in an image region."""
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)  # Flatten pixels
    counts = Counter(map(tuple, pixels))  # Count occurrences
    dominant_color = counts.most_common(1)[0][0]  # Get the most frequent color
    return dominant_color

def extract_text_colors(image_path, bounding_boxes):
    """Extracts the dominant color for each text bounding box."""
    image = Image.open(image_path).convert("RGB")  # Open and ensure RGB mode
    text_colors = []

    for box in bounding_boxes:
        bbox = box["bbox"]  # Extract bounding box coordinates

        # Get top-left and bottom-right corners from the four points
        x_min = min(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
        y_min = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
        x_max = max(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
        y_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])

        # Crop the text region
        text_region = image.crop((x_min, y_min, x_max, y_max))

        # Get dominant color
        dominant_color = get_dominant_color(text_region)

        # Convert to hex format
        color_hex = "#{:02x}{:02x}{:02x}".format(*dominant_color)
        text_colors.append(color_hex)

    return text_colors
