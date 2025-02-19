from django.urls import path

from . import views
from . import apis

urlpatterns = [
    # ex: /scraper/
    path("", views.index, name="index"),

    # API calls

    path("start/", apis.start, name="start"),
    path("generate-tags/", apis.generate_tags, name="generate_tags"),
]