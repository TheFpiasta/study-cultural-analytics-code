from django.urls import path
from . import views  # Import views from the current app

urlpatterns = [
    path('', views.chatBot_page, name='chatBot_page'),  # This route will render the page
    path('chat/', views.chat_with_llm, name='chat_with_llm'),
]