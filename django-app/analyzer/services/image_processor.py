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

    reader = None
    if analysis_config.get("ocr", True):
        reader = easyocr.Reader(['de'], gpu=True)

    base_dir = '/app' if os.path.exists('/app') else os.path.dirname(settings.BASE_DIR)
    images_base_folder = os.path.join(base_dir, "images")

    for folder_name in os.listdir(images_base_folder):
        folder_path = os.path.join(images_base_folder, folder_name)
        if not os.path.isdir(folder_path):
            continue

        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))][:2]

        if not image_files:
            yield yield_event(f"❌ No images found in {folder_name}")
            continue

        yield yield_event(f"📂 Processing images in {folder_name}...")

        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)
            existing_entry = AnalyzerResult.objects.using("analyzer_db").filter(image_name=image_file).first()

            if existing_entry:
                if existing_entry.processing_status == "completed":
                    yield yield_event(f"⏩ Skipping {image_file} (already processed).")
                    continue
                
                # If only OCR was done and further analysis is needed
                if existing_entry.processing_status == "ocr_done" and any(analysis_config.get(task, False) for task in ["color_analysis", "sentiment_analysis", "font_size"]):
                    yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry)
                continue  # Skip if nothing needs to be done

            # If no entry exists, process everything based on config
            yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config)


def process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry=None):
    yield yield_event(f"🔎 Analyzing {image_file}...")

    try:
        extracted_text, bounding_boxes = None, None
        avg_color_hex, text_colors, font_sizes, sentiment_vader, sentiment_llm = None, None, None, None, None

        # If OCR is required and not already performed
        if analysis_config.get("ocr", True) and (existing_entry is None or not existing_entry.ocr_text):
            extracted_text, bounding_boxes = run_ocr(image_path, reader)
        elif existing_entry:
            extracted_text = existing_entry.ocr_text
            bounding_boxes = json.loads(existing_entry.bounding_boxes) if existing_entry.bounding_boxes else None

        # Perform color analysis if required
        if analysis_config.get("color_analysis", True):
            avg_color = get_average_color(image_path)
            avg_color_hex = '#{:02x}{:02x}{:02x}'.format(*avg_color)

        # Extract text colors if OCR was performed
        if extracted_text and analysis_config.get("color_analysis", True):
            text_colors = extract_text_colors(image_path, bounding_boxes)

        # Sentiment analysis
        if extracted_text:
            cleaned_text = " ".join(extracted_text.splitlines())

            vader_polarity, vader_sentiment = None, None
            llm_polarity, llm_sentiment = None, None

            yield yield_event(f"📝 Analyzing sentiment for: {cleaned_text}")
                              
            if analysis_config.get("sentiment_analysis", True):
                vader_polarity, vader_sentiment = analyze_text_sentiment_vader(cleaned_text)
                yield yield_event(f"📊 Vader Sentiment result: {vader_sentiment}")
            
            if analysis_config.get("llm_sentiment", False):
                llm_sentiment = analyze_text_sentiment_llm(cleaned_text)
                yield yield_event(f"📊 LLM Sentiment result: {llm_sentiment}")
                    



        # if extracted_text and analysis_config.get("sentiment_analysis", True):
        #     cleaned_text = " ".join(extracted_text.splitlines())

        #     yield yield_event(f"📝 Analyzing sentiment for: {cleaned_text}")

        #     if analysis_config.get("llm_sentiment", False):
        #         sentiment_llm = analyze_text_sentiment_llm(cleaned_text)
        #         yield yield_event(f"📊 LLM Sentiment result: {sentiment_llm}")
        #     else:
        #         polarity, sentiment_vader = analyze_text_sentiment_vader(cleaned_text)

        # Font size estimation
        if bounding_boxes and analysis_config.get("font_size", True):
            font_sizes = estimate_font_size_opencv(image_path, bounding_boxes)

        # Update or create database entry
        if existing_entry:
            existing_entry.ocr_text = extracted_text or existing_entry.ocr_text
            existing_entry.bounding_boxes = json.dumps(bounding_boxes) if bounding_boxes else existing_entry.bounding_boxes
            existing_entry.background_color = avg_color_hex or existing_entry.background_color
            existing_entry.text_colors = json.dumps(text_colors) if text_colors else existing_entry.text_colors
            existing_entry.font_sizes = json.dumps(font_sizes) if font_sizes else existing_entry.font_sizes
            existing_entry.sentiment_vader = sentiment_vader or existing_entry.sentiment_vader
            existing_entry.sentiment_deepseek = sentiment_llm or existing_entry.sentiment_deepseek
            existing_entry.processing_status = "completed"
            existing_entry.save(using="analyzer_db")
        else:
            AnalyzerResult.objects.using("analyzer_db").create(
                image_name=image_file,
                created_at=timezone.now(),
                ocr_text=extracted_text,
                bounding_boxes=json.dumps(bounding_boxes) if bounding_boxes else None,
                background_color=avg_color_hex if avg_color_hex else None,
                text_colors=json.dumps(text_colors) if text_colors else None,
                font_sizes=json.dumps(font_sizes) if font_sizes else None,
                sentiment_vader=sentiment_vader if sentiment_vader else None,
                sentiment_deepseek=sentiment_llm if sentiment_llm else None,
                processing_status="completed"
            )

        yield yield_event(f"✅ {image_file} analyzed successfully.")

    except Exception as e:
        yield yield_event(f"❌ Error analyzing {image_file}: {str(e)}")