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

from scraper.models import ScrapeData

def process_images(yield_event, analysis_config):
    yield yield_event("🔍 Starting image processing...")

    reader = None
    if analysis_config.get("ocr", True):
        reader = easyocr.Reader(['de'], gpu=True)

    base_dir = '/app' if os.path.exists('/app') else os.path.dirname(settings.BASE_DIR)
    images_base_folder = os.path.join(base_dir, "images")

    # Get all folders (if any exist)
    folders = [folder for folder in os.listdir(images_base_folder) if os.path.isdir(os.path.join(images_base_folder, folder))]

    if len(folders) > 2:
        # Process all folders except the first two
        for folder in folders[2:]:
            folder_path = os.path.join(images_base_folder, folder)

            # Get all images in the folder
            image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))]

            if not image_files:
                yield yield_event(f"❌ No images found in {folder}")
            else:
                for image_file in image_files:
                    image_path = os.path.join(folder_path, image_file)
                    existing_entry = AnalyzerResult.objects.using("analyzer_db").filter(image_name=image_file).first()

                    if existing_entry and existing_entry.processing_status == "completed":
                        yield yield_event(f"⏩ Skipping {image_file} (already processed).")
                        continue

                    yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry)
    else:
        yield yield_event("❌ No sufficient folders found in the 'images' directory.")
    images_base_folder = os.path.join(base_dir, "images")

    # Get all folders (if any exist)
    folders = [folder for folder in os.listdir(images_base_folder) if os.path.isdir(os.path.join(images_base_folder, folder))]

    if len(folders) > 1:
        # Process only the second folder
        folder_path = os.path.join(images_base_folder, folders[1])

        # Get all images in the second folder
        image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))]

        if not image_files:
            yield yield_event(f"❌ No images found in {folders[1]}")
        else:
            # yield yield_event(f"📂 Processing all images in {folders[1]}...")

            for image_file in image_files:
                image_path = os.path.join(folder_path, image_file)
                existing_entry = AnalyzerResult.objects.using("analyzer_db").filter(image_name=image_file).first()

                if existing_entry and existing_entry.processing_status == "completed":
                    yield yield_event(f"⏩ Skipping {image_file} (already processed).")
                    continue

                yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry)
    else:
        yield yield_event("❌ No sufficient folders found in the 'images' directory.")


        # for image_file in image_files:
        #     image_path = os.path.join(folder_path, image_file)
        #     existing_entry = AnalyzerResult.objects.using("analyzer_db").filter(image_name=image_file).first()

        #     if existing_entry:
        #         if existing_entry.processing_status == "completed":
        #             yield yield_event(f"⏩ Skipping {image_file} (already processed).")
        #             continue
                
        #         # If only OCR was done and further analysis is needed
        #         if existing_entry.processing_status == "ocr_done" and any(analysis_config.get(task, False) for task in ["color_analysis", "sentiment_analysis", "font_size"]):
        #             yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry)
        #         continue  # Skip if nothing needs to be done

        #     # If no entry exists, process everything based on config
        #     yield from process_single_image(image_path, image_file, yield_event, reader, analysis_config)


def process_single_image(image_path, image_file, yield_event, reader, analysis_config, existing_entry=None):
    yield yield_event(f"🔎 Analyzing {image_file}...")

    try:
        extracted_text, bounding_boxes = None, None
        avg_color_hex, text_colors, font_sizes, sentiment_vader, sentiment_llm = None, None, None, None, None
        owner_id = None  # Initialize owner_id as None

        # Retrieve owner_id from ScrapeData in caprojectdb
        scrape_record = ScrapeData.objects.using("default").filter(img_name=image_file).first()

        if scrape_record:
            owner_id = scrape_record.owner_id  # Get the owner_id
            # yield yield_event(f"👤 Found owner_id: {owner_id} for {image_file}")

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

            vader_result = None
            deepseek_result = None

            # yield yield_event(f"📝 Analyzing sentiment for: {cleaned_text}")
                                
            if analysis_config.get("sentiment_analysis", True):
                vader_polarity, vader_sentiment = analyze_text_sentiment_vader(cleaned_text)
                vader_result = {"score": vader_polarity, "category": vader_sentiment}  # Store as JSON
                # yield yield_event(f"📊 VADER Sentiment result: {vader_result}")

            if analysis_config.get("llm_sentiment", False):
                llm_polarity, llm_sentiment = analyze_text_sentiment_llm(cleaned_text)
                deepseek_result = {"score": llm_polarity, "category": llm_sentiment}  # Store as JSON
                # yield yield_event(f"📊 LLM Sentiment result: {deepseek_result}")


            # Create a structured JSON object for sentiment results
            # text_sentiment = {
            #     "vader": {"score": vader_polarity, "sentiment": vader_sentiment} if vader_polarity is not None else None,
            #     "llm": {"score": llm_polarity, "sentiment": llm_sentiment} if llm_polarity is not None else None
            # }

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
            existing_entry.sentiment_vader = vader_result or existing_entry.sentiment_vader
            existing_entry.sentiment_deepseek = deepseek_result or existing_entry.sentiment_deepseek
            existing_entry.owner_id = owner_id or existing_entry.owner_id  # Store owner_id
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
                sentiment_vader=vader_result if vader_result else None,
                sentiment_deepseek=deepseek_result if deepseek_result else None,
                owner_id=owner_id,  # Store owner_id
                processing_status="completed"
            )


        # yield yield_event(f"✅ {image_file} analyzed successfully.")

    except Exception as e:
        yield yield_event(f"❌ Error analyzing {image_file}: {str(e)}")