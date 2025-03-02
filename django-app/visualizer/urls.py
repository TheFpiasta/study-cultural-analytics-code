from django.urls import path
from . import views  # Import views from the current app

urlpatterns = [
    path('', views.analyze_page, name='analyze_page'),  # This route will render the page
    path('analyze/', views.analyze_view, name='analyze'),
]