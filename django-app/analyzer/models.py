from django.db import models

class AnalyzerResult(models.Model):
    img_name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    scraper_datum_id = models.IntegerField(blank=True, null=True)
    ocr_text = models.TextField(blank=True, null=True)
    box_cord = models.TextField(blank=True, null=True)
    textfarben = models.CharField(max_length=30, blank=True, null=True)  # Increased for flexibility
    font_size = models.TextField(blank=True, null=True)
    hintergrundfarben = models.CharField(max_length=30, blank=True, null=True)  # Increased
    textstimmung = models.TextField(blank=True, null=True)  # Increased

    class Meta:
        app_label = 'analyzer'

    def __str__(self):
        return f"{self.img_name} - {self.created}"
