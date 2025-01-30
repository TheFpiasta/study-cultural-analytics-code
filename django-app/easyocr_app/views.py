import os
import time
import easyocr
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .models import OCRProcess  # Import the OCRProcess model


# Store messages globally (simple approach)
OCR_PROGRESS = []

def start_ocr_page(request):
    return render(request, 'start_ocr.html')

def ocr_process_stream(request):
    # Variable to control if images should be annotated and stored
    annotate_images = False  # Set to False to skip image annotation and storage

    def event_stream():
        # Yield initial message
        yield "data: 🚀 OCR process started...\n\n"
        
        # Simulate initialization message
        yield "data: 🔍 Initializing OCR engine (this may take a while)...\n\n"
        
        # Initialize OCR reader
        reader = easyocr.Reader(['de'])  # Initialize OCR reader (this will take time on CPU)
        yield "data: OCR engine initialized.\n\n"

        # Detect environment (Docker or Local)
        base_dir = '/app' if os.path.exists('/app') else os.path.dirname(settings.BASE_DIR)
        images_base_folder = os.path.join(base_dir, "images")
        analyzed_base_folder = os.path.join(base_dir, "annotated_images")
        
        # Creating the folder for annotated images if it's not created
        os.makedirs(analyzed_base_folder, exist_ok=True)

        if annotate_images:
            yield "data: 📝 Annotated images will be saved.\n\n"
        else:
            yield "data: 🗑 Annotated images will not be saved.\n\n"

        # Process image folders
        for folder_name in os.listdir(images_base_folder):
            folder_path = os.path.join(images_base_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue

            if annotate_images:
                output_folder = os.path.join(analyzed_base_folder, folder_name)
                os.makedirs(output_folder, exist_ok=True)

            image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))][:3]  # Limiting to first 3 images
            if not image_files:
                yield f"data: ⚠ No JPEG images found in {folder_name}. Skipping...\n\n"
                continue

            yield f"data: 📂 Processing {len(image_files)} images in '{folder_name}'...\n\n"

            for image_file in image_files:
                image_path = os.path.join(folder_path, image_file)

                # Skip the annotation and image saving if annotate_images is False
                if annotate_images:
                    annotated_path = os.path.join(output_folder, f"annotated_{image_file}")
                else:
                    annotated_path = None  # No annotation saved, not needed

                yield f"data: 🖼 Processing image: {image_file}...\n\n"

                try:
                    # Run OCR on the image
                    results = reader.readtext(image_path)
                    
                    # Initialize variables
                    recognized_text = ""
                    total_confidence = 0
                    num_confidences = 0

                    # If we are annotating, proceed with the image annotation
                    if annotate_images:
                        img = Image.open(image_path)
                        draw = ImageDraw.Draw(img)

                        try:
                            font = ImageFont.truetype("arial.ttf", size=16)
                        except IOError:
                            font = ImageFont.load_default()

                        for (bbox, text, confidence) in results:
                            if confidence <= 0.5:
                                continue
                            (top_left, _, bottom_right, _) = bbox
                            top_left = tuple(map(int, top_left))
                            bottom_right = tuple(map(int, bottom_right))
                            draw.rectangle([top_left, bottom_right], outline="red", width=3)
                            draw.text((top_left[0], top_left[1] - 20), text, fill="blue", font=font)
                            
                            recognized_text += text + "\n"
                            total_confidence += confidence
                            num_confidences += 1

                        if num_confidences > 0:
                            avg_confidence = total_confidence / num_confidences
                        else:
                            avg_confidence = 0

                        # Save annotated image if required
                        img.save(annotated_path)  # Save the annotated image
                    else:
                        # Just process the text and confidence without annotating or saving the image
                        for (bbox, text, confidence) in results:
                            if confidence <= 0.5:
                                continue
                            recognized_text += text + "\n"
                            total_confidence += confidence
                            num_confidences += 1

                        if num_confidences > 0:
                            avg_confidence = total_confidence / num_confidences
                        else:
                            avg_confidence = 0

                    # Create a new OCRProcess entry for each image processed
                    ocr_process = OCRProcess.objects.create(
                        original_image_path=image_path,
                        annotated_image_path=annotated_path,  # If image was annotated, save the path
                        recognized_text=recognized_text,
                        avg_confidence=avg_confidence,
                        status='success',  # Successfully processed this image
                    )

                    yield f"data: ✅ Processed: {image_file}\n\n"

                except Exception as e:
                    yield f"data: ❌ Error processing {image_file}: {str(e)}\n\n"

        # Final message
        yield "data: 🎉 OCR processing complete!\n\n"

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


# Start OCR process triggered by the button click
def start_ocr_process(request):
    if request.method == 'POST':
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

    """
    Function to process OCR for all pending jobs and update the database.
    This is the same logic that was previously in the Command class.
    """
    print("Starting OCR processing...")

    # Get pending OCR jobs
    pending_jobs = OCRProcess.objects.filter(status="pending")

    if not pending_jobs.exists():
        print("No pending OCR jobs found.")
        return

    # Initialize EasyOCR reader
    reader = easyocr.Reader(["en"])  # Add more languages if needed

    for job in pending_jobs:
        try:
            image_path = job.original_image_path

            # Check if image file exists
            if not os.path.exists(image_path):
                job.status = "failed"
                job.error_msg = f"File not found: {image_path}"
                job.save()
                print(f"Image not found: {image_path}")
                continue

            # Run OCR
            print(f"Processing: {image_path}")
            results = reader.readtext(image_path, detail=1)  # detail=1 returns bounding boxes & confidence

            # Extract text and confidence scores
            extracted_text = "\n".join([result[1] for result in results])
            avg_confidence = sum([result[2] for result in results]) / len(results) if results else 0.0

            # Update the database
            job.recognized_text = extracted_text
            job.avg_confidence = avg_confidence
            job.status = "success"
            job.created_at = now()  # Timestamp
            job.save()

            print(f"✔ Processed: {image_path} (Confidence: {avg_confidence:.2f})")

        except Exception as e:
            job.status = "failed"
            job.error_msg = str(e)
            job.save()
            print(f"Failed processing {image_path}: {e}")

    print("OCR processing complete!")