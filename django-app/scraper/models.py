from datetime import datetime, date

from django.db import models
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.http import JsonResponse


def validate_run_status(value):
    valid_statuses = ["created", "running", "error", "finished"]
    if value not in valid_statuses:
        raise ValidationError(f'{value} is not a valid status of {valid_statuses}.')

def validate_img_status(value):
    valid_statuses = ["success", "failed"]
    if value not in valid_statuses:
        raise ValidationError(f'{value} is not a valid status of {valid_statuses}.')


class ScraperRun(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')

    name = models.CharField(max_length=100)
    profile_id = models.BigIntegerField()
    start_cursor = models.TextField(null=True, blank=True)

    scrape_max_date = models.DateField(default=date.min)
    scrape_max_nodes = models.IntegerField()
    scrape_max_batches = models.SmallIntegerField()
    scrape_nodes_per_batch = models.SmallIntegerField()

    status = models.CharField(max_length=100, validators=[validate_run_status])
    error_msg = models.TextField(null=True, blank=True)
    total_data_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    img_dir = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.id}: {self.name} ({self.status}) - {self.created_at}"

    def to_json(self):
        return JsonResponse(serialize('json', [self]), safe=False)


class ScrapeBatch(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    scraper_run_id = models.ForeignKey(ScraperRun, on_delete=models.CASCADE)
    nodes_in_batch = models.SmallIntegerField()
    has_next_page = models.BooleanField()
    end_cursor = models.TextField(null=True, blank=True)
    status = models.TextField()
    extensions = models.TextField()
    response_on_error = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: run:{self.scraper_run_id_id}, {self.status}"

    def to_json(self):
        return JsonResponse(serialize('json', [self]), safe=False)


class ScrapeData(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    scraper_run_id = models.ForeignKey(ScraperRun, on_delete=models.CASCADE)
    scrape_batch_id = models.ForeignKey(ScrapeBatch, on_delete=models.CASCADE)

    node_id = models.BigIntegerField()
    type = models.CharField(max_length=100)
    text = models.TextField()
    shortcode = models.CharField(max_length=100)
    comment_count = models.IntegerField()
    comments_disabled = models.BooleanField()
    taken_at_timestamp = models.IntegerField()

    display_height = models.IntegerField()
    display_width = models.IntegerField()
    display_url = models.TextField()
    img_name = models.TextField(null=True, blank=True)
    img_download_status = models.CharField(max_length=100, validators=[validate_img_status], null=True, blank=True)

    likes_count = models.IntegerField()
    owner_id = models.BigIntegerField()

    thumbnail_src = models.TextField()
    thumbnail_resources = models.TextField()

    is_video = models.BooleanField()

    extracted_hashtags = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: run:{self.scraper_run_id_id}, batch:{self.scrape_batch_id_id}, shortcode:{self.shortcode}, {self.img_name}, {self.img_download_status}"

    def to_json(self):
        return JsonResponse(serialize('json', [self]), safe=False)
