from django.urls import path
from . import views  # Import views from the current app



urlpatterns = [
    path('', views.analyze_page, name='analyze_page'),  # This route will render the page
    path('analyze/', views.analyze_view, name='analyze'),
    path('likes-vs-sentiment/', views.likes_vs_sentiment_view, name='likes_vs_sentiment'),
    path('background-color-vs-sentiment/', views.background_color_vs_sentiment_view, name='background_color_vs_sentiment'),
    path('text-color-vs-background-color/', views.text_color_vs_background_color_view, name='text_color_vs_background_color'),
    path('likes-over-time/', views.likes_over_time_view, name='likes_over_time'),
    path('sentiment-over-time/', views.sentiment_over_time_view, name='sentiment_over_time'),
    path('background-color-over-time/', views.background_color_over_time_view, name='background_color_over_time'),
    path('font-size-per-portal/', views.font_size_per_portal_view, name='font_size_per_portal'),

    path('sentiment-per-portal-over-time/', views.sentiment_per_portal_over_time_view, name='sentiment_per_portal_over_time'),
    path('likes-per-portal-over-time/', views.likes_per_portal_over_time_view, name='likes_per_portal_over_time'),
    path('hashtag-group-usage/', views.hashtag_group_usage_view, name='hashtag_group_usage'),
    path('hashtag-group-percentage/', views.hashtag_group_percentage_view, name='hashtag_group_percentage'),
    path('avg-likes-per-hashtag-group/', views.avg_likes_per_hashtag_group_view, name='avg_likes_per_hashtag_group'),
    path('comment-count-per-hashtag-group/', views.comment_count_per_hashtag_group_view, name='comment_count_per_hashtag_group'),
    path('sentiment-radial/', views.sentiment_radial_view, name='sentiment_radial'),
    path('sentiment-radial-bild/', views.sentiment_radial_bild_view, name='sentiment_radial_bild'),
    path('sentiment-radial-sz/', views.sentiment_radial_sz_view, name='sentiment_radial_sz'),
    path('top-hashtags-over-time/', views.top_hashtags_over_time_view, name='top_hashtags_over_time'),
    path('dominant-background-colors/', views.dominant_background_colors_view, name='dominant_background_colors'),
    path('text-space-usage/', views.text_space_usage_view, name='text_space_usage'),
    path('background-color-radial/<int:portal_id>/', views.background_color_radial_view, name='background_color_radial'),
    path('text-color-usage-radial/', views.text_color_usage_radial_view, name='text_color_usage_radial'),
    path('text-color-usage-bar/', views.text_color_usage_bar_view, name='text_color_usage_bar'),
    path('hashtag-group-usage-radial-bild/', views.hashtag_group_usage_radial_bild_view, name='hashtag_group_usage_radial_bild'),
    path('hashtag-group-usage-radial-zdf/', views.hashtag_group_usage_radial_zdf_view, name='hashtag_group_usage_radial_zdf'),
    path('hashtag-group-usage-radial-sz/', views.hashtag_group_usage_radial_sz_view, name='hashtag_group_usage_radial_sz'),
    path('text-vs-background-luminance/', views.text_vs_background_luminance_view, name='text_vs_background_luminance'),
    path('text-vs-background-color/', views.text_vs_background_color_view, name='text_vs_background_color'),
]



# -- ausreißer mit einbeziehen

# -- hastags je portal und deepseek
# -- 3 häufigste je hastags und portal
# -- wie stark nutzen die portale die hastgasgruppen
# -- wie viele posts pro Gruppe und likes



# -- immer wie viel von der Gruppe
# -- rdialdiagramme stimmung (je Portal) (alsbalken ) und für hintergrundfarbe und textplatznutzung (alle vier diagramme)
# -- dominanteste hintegrundfarbe pro portal mit punkten die für die Verwendung stehen und Portalen
# -- platznutzung über die Zeit 



# -- immer jedes Portal einzeichnen
