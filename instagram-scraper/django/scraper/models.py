from django.db import models

# Create your models here.

class ScrapeBatch(models.Model):
    size = models.IntegerField()
    end_cursor = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}, {self.size}, {self.end_cursor}, {self.created_at}"

    def no_size_or_final(self):
        return self.size == 0 or self.end_cursor is ""

class ScrapeData(models.Model):
    scrape_batch_id = models.ForeignKey(ScrapeBatch, on_delete=models.CASCADE)
    node_iid = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
