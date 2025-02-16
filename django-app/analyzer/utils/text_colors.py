import cv2
import numpy as np
from PIL import Image
from collections import Counter

def get_dominant_color(image):
    """Returns the most common (dominant) color in an image region."""
    pixels = np.array(image)
    pixels = pixels.reshape(-1, 3)  # Flatten pixels
    counts = Counter(map(tuple, pixels))  # Count occurrences
    dominant_color = counts.most_common(1)[0][0]  # Get the most frequent color
    return dominant_color

def extract_text_colors_from_box(image, bbox):
    """Extracts the dominant color for individual letters inside a bounding box."""
    # bbox is a list of 4 points: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
    # Convert the bounding box coordinates to a format OpenCV can work with (rectangle)
    x_min = min([point[0] for point in bbox])
    y_min = min([point[1] for point in bbox])
    x_max = max([point[0] for point in bbox])
    y_max = max([point[1] for point in bbox])

    # Crop the region within the bounding box
    text_region = image[y_min:y_max, x_min:x_max]
    
    # Convert to grayscale for better letter segmentation
    gray_image = cv2.cvtColor(text_region, cv2.COLOR_BGR2GRAY)
    
    # Threshold the image to get a binary image (black and white)
    _, thresh = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours to detect individual letters
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    letter_colors = []

    for contour in contours:
        if cv2.contourArea(contour) < 100:  # Filter out small noise contours
            continue
        
        # Get bounding box for each individual letter
        x, y, w, h = cv2.boundingRect(contour)
        
        # Crop the letter
        letter_region = text_region[y:y+h, x:x+w]
        
        # Get the dominant color for the letter
        dominant_color = get_dominant_color(letter_region)
        
        # Append the dominant color (RGB)
        letter_colors.append(dominant_color)
    
    # If we have detected colors, return the most frequent one
    if letter_colors:
        return Counter(letter_colors).most_common(1)[0][0]
    else:
        return (255, 255, 255)  # Default to white if no text found

def extract_text_colors(image_path, bounding_boxes):
    """Extracts the text color for each bounding box (focused on individual letters)."""
    image = cv2.imread(image_path)  # Open image using OpenCV
    text_colors = []

    for box in bounding_boxes:
        bbox = box["bbox"]
        
        # Extract the dominant color for each bounding box
        text_color = extract_text_colors_from_box(image, bbox)

        # Convert the color to Hex format
        color_hex = "#{:02x}{:02x}{:02x}".format(*text_color)
        text_colors.append(color_hex)

    return text_colors
