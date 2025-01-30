# Generated by Django 5.1.4 on 2025-01-30 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('easyocr_app', '0002_ocrprocess'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UploadedImage',
        ),
        migrations.AlterField(
            model_name='ocrprocess',
            name='avg_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ocrprocess',
            name='recognized_text',
            field=models.TextField(blank=True, null=True),
        ),
    ]
