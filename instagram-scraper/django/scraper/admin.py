from django.contrib import admin

# Register your models here.

from .models import ScrapeData
from .models import ScrapeBatch

admin.site.register(ScrapeData)
admin.site.register(ScrapeBatch)