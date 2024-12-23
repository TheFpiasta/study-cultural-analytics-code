from django.contrib import admin

# Register your models here.

from .models import ScrapeData, ScraperRun, ScrapeBatch

admin.site.register(ScraperRun)
admin.site.register(ScrapeBatch)
admin.site.register(ScrapeData)
