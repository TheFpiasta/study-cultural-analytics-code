from django.db import models
import os

class OCRProcess(models.Model):
    id = models.BigAutoField(primary_key=True)
    
    # The original image path (including folder and image name)
    original_image_path = models.TextField()
    
    # Path to the annotated image (optional)
    annotated_image_path = models.TextField(null=True, blank=True)

    # Extracted text from the image
    recognized_text = models.TextField(null=True, blank=True)

    # Average confidence of OCR recognition
    avg_confidence = models.FloatField(null=True, blank=True)

    # Status of the OCR process
    status = models.CharField(max_length=100, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ], default='pending')

    # Error message (if any)
    error_msg = models.TextField(null=True, blank=True)

    # Date & time of processing
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OCR {self.id}: {os.path.basename(self.original_image_path)} - {self.status}"
