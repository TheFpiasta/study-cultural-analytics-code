import os
import json
import easyocr
from django.utils import timezone
from analyzer.utils.easyocr import run_ocr
from analyzer.utils.color_analysis import get_average_color
from analyzer.utils.text_colors import extract_text_colors
from analyzer.utils.text_sentiment import analyze_text_sentiment
from analyzer.models import AnalyzerResult

def process_images(yield_event):
    yield yield_event("🔍 Starting image processing...")

    # Initialize EasyOCR Reader once (outside the loop)
    reader = easyocr.Reader(['de'])

    base_dir = '/app' if os.path.exists('/app') else os.path.dirname(settings.BASE_DIR)

    images_base_folder = os.path.join(base_dir, "images")

    for folder_name in os.listdir(images_base_folder):
        folder_path = os.path.join(images_base_folder, folder_name)

        if not os.path.isdir(folder_path): 
            continue

        image_files =  [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))][:1] # Limit
        
        if not image_files:
            yield yield_event(f"❌ No images found in {folder_name}")
            continue

        yield yield_event(f"📂 Processing images in {folder_name}...")

        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)

            existing_entry = AnalyzerResult.objects.filter(img_name=image_file).first()

            if existing_entry:
                yield yield_event(f"⏩ Skipping {image_file} as it has already been processed.")
                continue

            yield from process_single_image(image_path, image_file, yield_event, reader)

def process_single_image(image_path, image_file, yield_event, reader):
    """Processes a single image and streams updates."""
    yield yield_event(f"🔎 Analyzing {image_file}...")

    try:
        # Now we get the OCR result as a tuple (recognized_text, avg_confidence, bounding_boxes)
        extracted_text, bounding_boxes = run_ocr(image_path, reader)

        # Calculate average color of the image
        avg_color = get_average_color(image_path)
        avg_color_hex = '#{:02x}{:02x}{:02x}'.format(*avg_color)  # Convert RGB to Hex

        # Extract dominant colors for each text region
        text_colors = extract_text_colors(image_path, bounding_boxes)

        # Store text colors as JSON (so each text segment has its corresponding color)
        text_colors_json = json.dumps(text_colors)

        # Store the results in the database (AnalyzerResult model)
        ocr_result = AnalyzerResult(
            img_name=image_file,
            created=timezone.now(),
            scraper_datum_id=None,
            ocr_text=extracted_text,
            box_cord=json.dumps(bounding_boxes),
            textfarben=text_colors_json,
            font_size=None,
            hintergrundfarben=avg_color_hex,
            textstimmung=None
        )
        ocr_result.save(using="analyzer_db")

        yield yield_event(f"✅ {image_file} analyzed successfully.")
    
    except Exception as e:
        yield yield_event(f"❌ Error analyzing {image_file}: {str(e)}")