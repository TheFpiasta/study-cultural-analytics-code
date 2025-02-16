import os
import easyocr
from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Process images from all folders inside 'data/images/' and save annotated versions"

    def handle(self, *args, **kwargs):
        # Define paths
        base_dir = os.path.dirname(settings.BASE_DIR)  # Go one level up from django-app
        images_base_folder = os.path.join(base_dir, "data", "images")
        analyzed_base_folder = os.path.join(base_dir, "data", "analyzed_images")

        # Ensure the analyzed_images base folder exists
        os.makedirs(analyzed_base_folder, exist_ok=True)

        # Initialize the EasyOCR reader (adjust language as needed)
        reader = easyocr.Reader(['de'])

        # Loop through all subfolders inside 'images/'
        for folder_name in os.listdir(images_base_folder):
            folder_path = os.path.join(images_base_folder, folder_name)

            # Ensure it's a directory (not a file)
            if not os.path.isdir(folder_path):
                continue

            # Define output folder for this specific subfolder
            output_folder = os.path.join(analyzed_base_folder, folder_name)
            os.makedirs(output_folder, exist_ok=True)

            # List the first 10 JPEG images in this folder
            image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg'))][:10]

            if not image_files:
                self.stdout.write(self.style.WARNING(f"No JPEG images found in {folder_name}. Skipping..."))
                continue

            self.stdout.write(self.style.SUCCESS(f"Processing {len(image_files)} images in '{folder_name}'..."))

            for image_file in image_files:
                image_path = os.path.join(folder_path, image_file)
                annotated_path = os.path.join(output_folder, f"annotated_{image_file}")

                try:
                    # Process the image with EasyOCR
                    results = reader.readtext(image_path)

                    # Open image for annotation
                    img = Image.open(image_path)
                    draw = ImageDraw.Draw(img)

                    # Load a font (fallback to default if not found)
                    try:
                        font = ImageFont.truetype("arial.ttf", size=16)
                    except IOError:
                        font = ImageFont.load_default()

                    # Draw bounding boxes and text
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
                    img.save(annotated_path)
                    self.stdout.write(self.style.SUCCESS(f"Processed: {image_file} → {annotated_path}"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {image_file} in {folder_name}: {e}"))

        self.stdout.write(self.style.SUCCESS("Processing complete! 🎉"))
