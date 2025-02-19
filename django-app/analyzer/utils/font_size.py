import cv2
import numpy as np
from PIL import Image

def get_image_dpi(image_path):
    """
    Attempts to get the DPI from the image metadata using Pillow.
    Returns a default DPI (96) if not found.
    """
    try:
        img = Image.open(image_path)
        dpi = img.info.get("dpi")  # Some formats store DPI here
        if dpi:
            return dpi[0]  # Extract DPI value (usually a tuple like (96, 96))
    except Exception as e:
        print(f"Could not read DPI from metadata: {e}")
    return 96  # Default DPI if unknown

def estimate_font_size_opencv(image_path, bounding_boxes):
    """
    Estimates font sizes for each bounding box and converts to pt.
    
    :param image_path: Path to the image file.
    :param bounding_boxes: List of bounding boxes from OCR, each with format {'text': str, 'bbox': [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]}.
    :return: List of estimated font sizes in pt for each bounding box.
    """
    # Load image (to check dimensions if needed)
    image = cv2.imread(image_path)
    
    # Get the image DPI
    dpi = get_image_dpi(image_path)

    font_sizes = []

    for box in bounding_boxes:
        # Extract Y-coordinates from the bounding box
        y_coords = [point[1] for point in box["bbox"]]
        
        # Calculate bounding box height in pixels
        bbox_height_px = max(y_coords) - min(y_coords)

        # Convert px to pt
        font_size_pt = (bbox_height_px / dpi) * 72

        # Append rounded font size
        font_sizes.append(round(font_size_pt, 2))

    return font_sizes
