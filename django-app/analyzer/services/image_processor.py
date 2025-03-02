import os
import json
import easyocr
# import torch

from django.utils import timezone
from analyzer.utils.easyocr import run_ocr
from analyzer.utils.color_analysis import get_average_color
from analyzer.utils.text_colors import extract_text_colors
from analyzer.utils.text_sentiments import analyze_text_sentiment
from analyzer.utils.vaderSentiment import analyze_text_sentiment_vader
from analyzer.utils.llm_sentiment import analyze_text_sentiment_llm
from analyzer.utils.font_size import estimate_font_size_opencv
from analyzer.models import AnalyzerResult

def process_images(yield_event, analysis_config):
    yield yield_event("🔍 Starting image processing...")

    # Initialize EasyOCR Reader only if OCR is enabled
    reader = None
    if analysis_config.get("ocr", True):
        import easyocr
        reader = easyocr.Reader(['de'], gpu=True)

    base_dir = '/app' if os.path.exists('/app') else os.path.dirname(settings.BASE_DIR)
    images_base_folder = os.path.join(base_dir, "images")

    for folder_name in os.listdir(images_base_folder):
        folder_path = os.path.join(images_base_folder, folder_name)
        if not os.path.isdir(folder_path): 
            continue

        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))][:1]

        if not image_files:
            yield yield_event(f"❌ No images found in {folder_name}")
            continue

        yield yield_event(f"📂 Processing images in {folder_name}...")

        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)
            existing_entry = AnalyzerResult.objects.filter(img_name=image_file).first()

            if existing_entry:
                yield yield_event(f"⏩ Skipping {image_file} (already processed).")
                continue

            yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config)


def process_single_image(image_path, image_file, yield_event, reader, analysis_config):
    """Processes a single image based on selected analyses."""
    yield yield_event(f"🔎 Analyzing {image_file}...")

    try:
        extracted_text, bounding_boxes = None, None
        avg_color_hex, text_colors, font_sizes, sentiment = None, None, None, None

        # Perform OCR if selected
        if analysis_config.get("ocr", True) and reader:
            from analyzer.utils.easyocr import run_ocr
            extracted_text, bounding_boxes = run_ocr(image_path, reader)

        # Perform color analysis if selected
        if analysis_config.get("color_analysis", True):
            from analyzer.utils.color_analysis import get_average_color
            avg_color = get_average_color(image_path)
            avg_color_hex = '#{:02x}{:02x}{:02x}'.format(*avg_color)

        # Extract text colors if OCR was performed
        if analysis_config.get("ocr", True) and analysis_config.get("color_analysis", True) and bounding_boxes:
            from analyzer.utils.text_colors import extract_text_colors
            text_colors = extract_text_colors(image_path, bounding_boxes)

        # Perform sentiment analysis if selected
        # if analysis_config.get("sentiment_analysis", True) and extracted_text:
        #     from analyzer.utils.vaderSentiment import analyze_text_sentiment_vader
        #     cleaned_text = " ".join(extracted_text.splitlines())
        #     polarity, sentiment = analyze_text_sentiment_vader(cleaned_text)
        # else:
        #     polarity, sentiment = None, None

        use_llm_for_sentiment = analysis_config.get("llm_sentiment", False)

        if analysis_config.get("sentiment_analysis", True) and extracted_text:
            cleaned_text = " ".join(extracted_text.splitlines())

            yield yield_event(f"📝 Analyzing sentiment for: {cleaned_text}") 

            yield yield_event(f"🔍 Using LLM for sentiment analysis.") if use_llm_for_sentiment else yield_event(f"🔍 Using VADER for sentiment analysis.")

            if use_llm_for_sentiment:
                sentiment = analyze_text_sentiment_llm(cleaned_text)

                yield yield_event(f"📊 Sentiment analysis result: {sentiment}")
            else:
                polarity, sentiment = analyze_text_sentiment_vader(cleaned_text)
        else:
            polarity, sentiment = None, None

        # Detect font size if selected
        if analysis_config.get("font_size", True) and bounding_boxes:
            from analyzer.utils.font_size import estimate_font_size_opencv
            font_sizes = estimate_font_size_opencv(image_path, bounding_boxes)

        # Store results in the database
        from django.utils import timezone
        from analyzer.models import AnalyzerResult
        ocr_result = AnalyzerResult(
            img_name=image_file,
            created=timezone.now(),
            scraper_datum_id=None,
            ocr_text=extracted_text,
            box_cord=json.dumps(bounding_boxes) if bounding_boxes else None,
            textfarben=json.dumps(text_colors) if text_colors else None,
            font_size=json.dumps(font_sizes) if font_sizes else None,
            hintergrundfarben=avg_color_hex if avg_color_hex else None,
            textstimmung=json.dumps(sentiment) if sentiment else None
        )
        ocr_result.save(using="analyzer_db")

        yield yield_event(f"✅ {image_file} analyzed successfully.")
    
    except Exception as e:
        yield yield_event(f"❌ Error analyzing {image_file}: {str(e)}")
