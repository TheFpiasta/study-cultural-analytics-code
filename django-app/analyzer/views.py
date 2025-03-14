import os
import time
import easyocr
import numpy as np
import json

import io
import base64

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.shortcuts import render
from django.http import FileResponse
from django.core.paginator import Paginator
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone  # For timestamp

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from analyzer.services.image_processor import process_images

from analyzer.models import AnalyzerResult  # Import the model
from scraper.models import ScrapeData

# Define the base path where images are stored
IMAGE_FOLDER_PATH = os.path.join(settings.BASE_DIR, 'data', 'images')

def list_images(request, folder_name=None):
    # Get all subfolders in 'data/images'
    folders = [folder for folder in os.listdir(IMAGE_FOLDER_PATH) if os.path.isdir(os.path.join(IMAGE_FOLDER_PATH, folder))]

    # If a folder name is specified, get images from that folder
    if folder_name:
        folder_path = os.path.join(IMAGE_FOLDER_PATH, folder_name)
        if os.path.isdir(folder_path):
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))]
            # Pagination: Show only first 50 images
            paginator = Paginator(images, 20)  # Show 50 images per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # Retrieve OCR data for each image
            image_data = []
            for image in page_obj:
                try:
                    # Fetch OCR result for the image
                    anylyzer_result = AnalyzerResult.objects.get(img_name=image)
                    image_data.append({
                        'image_name': image,
                        'text': anylyzer_result.ocr_text,
                        'avg_color': anylyzer_result.hintergrundfarben,
                        'text_boxes': anylyzer_result.box_cord,
                        'text_colors': json.dumps(anylyzer_result.textfarben) if anylyzer_result.textfarben else "[]",
                        'font_size': json.dumps(anylyzer_result.font_size) if anylyzer_result.font_size else "[]",
                        'text_sentiment': anylyzer_result.textstimmung if anylyzer_result.textstimmung else "{}",
                    })

                except AnalyzerResult.DoesNotExist:
                    image_data.append({
                        'image_name': image,
                        'text': None,
                        'avg_color': None,
                        'text_boxes': None,
                        'text_colors': None,
                        'font_size': None,
                        'text_sentiment': None,
                    })
                
            return render(request, 'analyzer/image_gallery.html', {
                'folder_name': folder_name,
                'page_obj': page_obj,
                'folders': folders,
                'image_data': image_data,
            })

    return render(request, 'analyzer/folder_list.html', {'folders': folders})

def serve_image(request, folder_name, image_name):
    image_path = os.path.join(settings.BASE_DIR, 'data', 'images', folder_name, image_name)
    if os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
    else:
        return HttpResponseNotFound("Image not found")

def get_average_color(image_path):
    image = Image.open(image_path)
    image = image.convert('RGB')  # Ensure the image is in RGB mode
    np_image = np.array(image)  # Convert to numpy array
    avg_color = np.mean(np_image, axis=(0, 1))  # Compute average color over all pixels
    return tuple(map(int, avg_color))  # Return as RGB tuple

# Store messages globally (simple approach)
OCR_PROGRESS = []

def start_ocr_page(request):
    return render(request, 'start_ocr.html')

def yield_event(message):
    """Send progress updates to the frontend immediately."""
    return f"data: {message}\n\n"

def ocr_process_stream(request):
    """Handles OCR streaming response."""
    
    analysis_config = request.session.get("analysis_config", {
        "ocr": True,
        "color_analysis": True,
        "sentiment_analysis": True,
        "font_size": True,
        "llm_sentiment": False,
    })

    def event_stream():
        start_time = time.time()
        yield "data: config: " + json.dumps(analysis_config) + "\n\n"
        yield "data: 🚀 Analyzing process started...\n\n"

        # Clear previous results
        # AnalyzerResult.objects.using("analyzer_db").all().delete()
        # yield "data: 🗑 Cleared previous results from DB...\n\n"
        
        # Start image processing
        for message in process_images(yield_event, analysis_config):
            yield message  

        elapsed_time = time.time() - start_time
        yield f"data: ⏱️ Processing complete! Elapsed time: {elapsed_time:.2f} seconds.\n\n"
        yield "data: 🎉 Analyzing processing complete!\n\n"

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


# Start OCR process triggered by the button click
def start_ocr_process(request):
    if request.method == 'POST':
        # Parse the JSON request body
        body_data = json.loads(request.body)

        # Store selected options in session (or another method like a database)
        request.session["analysis_config"] = body_data 

        return JsonResponse({'status': 'success', 'message': 'OCR process started successfully'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def ocr_view(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded image to the database
            uploaded_image = form.save()

            # Path to the uploaded image
            image_path = uploaded_image.image.path

            # Create an EasyOCR reader
            reader = easyocr.Reader(['de'])  # Adjust to the language you're using

            # Process the image with EasyOCR
            results = reader.readtext(image_path)

            # Open the image with PIL for annotation
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)

            # Optional: Load a font for drawing text (adjust path to a TTF file if needed)
            try:
                font = ImageFont.truetype("arial.ttf", size=16)  # You can use any TTF font here
            except IOError:
                font = ImageFont.load_default()

            # Draw bounding boxes and text on the image
            for (bbox, text, confidence) in results:
                if confidence <= 0.5:
                    continue  # Skip low-confidence text
                
                # Get coordinates for the bounding box
                (top_left, top_right, bottom_right, bottom_left) = bbox
                top_left = tuple(map(int, top_left))
                bottom_right = tuple(map(int, bottom_right))

                # Draw rectangle and text
                draw.rectangle([top_left, bottom_right], outline="red", width=3)
                draw.text((top_left[0], top_left[1] - 20), text, fill="blue", font=font)

            # Save the annotated image
            result_path = os.path.join(settings.MEDIA_ROOT, 'results', f"annotated_{uploaded_image.image.name}")
            os.makedirs(os.path.dirname(result_path), exist_ok=True)
            img.save(result_path)

            # Save result to the database
            uploaded_image.result_image.name = result_path.replace(settings.MEDIA_ROOT + '/', '')
            uploaded_image.recognized_text = "\n".join([text for (_, text, _) in results])
            uploaded_image.save()

            # Return the result image and recognized text
            return render(request, 'easyocr_app/results.html', {'image': uploaded_image})

    else:
        form = ImageUploadForm()

    return render(request, 'easyocr_app/upload.html', {'form': form})
