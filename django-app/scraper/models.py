from django.db import models

# Create your models here.


class ScraperRun(models.Model):
    total_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class ScrapeBatch(models.Model):
    scraper_run_id = models.ForeignKey(ScraperRun, on_delete=models.CASCADE)
    size = models.SmallIntegerField()
    end_cursor = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}, {self.size}, {self.end_cursor}, {self.created_at}"

    def no_size_or_final(self):
        return self.size == 0 or self.end_cursor == ""

class ScrapeData(models.Model):
    scrape_batch_id = models.ForeignKey(ScrapeBatch, on_delete=models.CASCADE)
    node_iid = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
