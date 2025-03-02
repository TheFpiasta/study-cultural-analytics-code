from django.urls import path
from . import views  # Import views from the current app

urlpatterns = [
    path('', views.start_ocr_page, name='start_ocr_page'),  # This route will render the page
    path('load_ocr', views.ocr_view, name='ocr_view'),
    path('start-ocr/', views.start_ocr_process, name='start_ocr_process'),  # This route will handle the button click
    path('ocr-stream/', views.ocr_process_stream, name='ocr_process_stream'),
    path('explorer/', views.list_images, name='folder_list'),
    path('explorer/folder/<str:folder_name>/', views.list_images, name='folder_images'),
    path('explorer/images/<str:folder_name>/<str:image_name>/', views.serve_image, name='serve_image'),  # New URL for serving images
]
