from datetime import datetime, date

from django.db import models
from django.core.exceptions import ValidationError
from django.core.serializers import serialize
from django.http import JsonResponse


def validate_run_status(value):
    valid_statuses = ["created", "running", "error", "finished"]
    if value not in valid_statuses:
        raise ValidationError(f'{value} is not a valid status of {valid_statuses}.')


class ScraperRun(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')

    name = models.CharField(max_length=100)
    profile_id = models.BigIntegerField()
    start_cursor = models.TextField(null=True, blank=True)

    scrape_max_date = models.DateField(default=date.min)
    scrape_max_notes = models.IntegerField()
    scrape_max_batches = models.SmallIntegerField()
    scrape_notes_per_batch = models.SmallIntegerField()

    status = models.CharField(max_length=100, validators=[validate_run_status])
    total_data_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.name} ({self.status}) - {self.created_at}"

    def to_json(self):
        return JsonResponse(serialize('json', [self]), safe=False)


class ScrapeBatch(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    scraper_run_id = models.ForeignKey(ScraperRun, on_delete=models.CASCADE)
    notes_in_batch = models.SmallIntegerField()
    has_next_page = models.BooleanField()
    end_cursor = models.TextField(null=True, blank=True)
    status = models.TextField()
    extensions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.scraper_run_id}, {self.size}, {self.has_next_page}, {self.end_cursor}, {self.status}, {self.extensions}, {self.created_at}"

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

    likes_count = models.IntegerField()
    owner_id = models.BigIntegerField()

    thumbnail_src = models.TextField()
    thumbnail_resources = models.TextField()

    is_video = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.scraper_run_id}, {self.scrape_batch_id}, {self.node_id}, {self.type}, {self.text[:16]}..., {self.shortcode}, {self.comment_count}, {self.comments_disabled}, {self.taken_at_timestamp}, {self.display_height}, {self.display_width}, {self.display_url[:16]}..., {self.likes_count}, {self.owner_id}, {self.thumbnail_src[:16]}..., {self.thumbnail_resources[:16]}..., {self.is_video}, {self.created_at}"

    def to_json(self):
        return JsonResponse(serialize('json', [self]), safe=False)
