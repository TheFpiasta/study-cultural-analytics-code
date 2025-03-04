from django.db import models
from django.utils import timezone

class AnalyzerResult(models.Model):
    image_name = models.CharField(max_length=255, unique=True)  # Renamed from img_name
    created_at = models.DateTimeField(default=timezone.now)  # Renamed from created
    ocr_text = models.TextField(null=True, blank=True)
    bounding_boxes = models.TextField(null=True, blank=True)  # Renamed from box_cord
    text_colors = models.TextField(null=True, blank=True)  # Renamed from textfarben
    font_sizes = models.TextField(null=True, blank=True)  # Renamed from font_size
    background_color = models.CharField(max_length=10, null=True, blank=True)  # Renamed from hintergrundfarben
    
    sentiment_vader = models.TextField(null=True, blank=True)  # VADER Sentiment
    sentiment_deepseek = models.TextField(null=True, blank=True)  # DeepSeek Coder Sentiment

    processing_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("ocr_done", "OCR Done"),
            ("completed", "Completed"),
        ],
        default="pending",
    )

    class Meta:
        app_label = "analyzer"

    def __str__(self):
        return f"{self.image_name} - {self.created_at}"
