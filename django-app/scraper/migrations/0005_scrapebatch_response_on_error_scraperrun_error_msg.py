# Generated by Django 5.1.4 on 2025-01-26 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0004_scrapedata_img_download_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='scrapebatch',
            name='response_on_error',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='scraperrun',
            name='error_msg',
            field=models.TextField(blank=True, null=True),
        ),
    ]
