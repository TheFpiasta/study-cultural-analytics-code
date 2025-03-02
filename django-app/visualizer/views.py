import json
import requests
import os
import re
from collections import defaultdict
from django.conf import settings

from django.shortcuts import render
from django.http import JsonResponse
from analyzer.models import AnalyzerResult
from scraper.models import ScrapeData

# Load the mapping JSON file
MAPPING_FILE_PATH = os.path.join(settings.BASE_DIR, "data", "mapping_hashtag_cluster_group", "mapping.json")

def load_mapping():
    """Load JSON data from mapping.json"""
    if not os.path.exists(MAPPING_FILE_PATH):
        return {"error": "File not found"}

    try:
        with open(MAPPING_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}

# Load hashtag mappings
mapping_data = load_mapping()
reversed_mapping = mapping_data.get("reversed_mapping", {})
    
def extract_hashtags(text):
    """Extract hashtags from text"""
    return re.findall(r"#\w+", text)

def is_numeric(value):
    """Helper function to check if a value is numeric."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def analyze_view(request):
    """Visualize mapped hashtag groups with like counts"""
    x_field = request.GET.get('x_field', 'hashtag_groups')
    y_field = request.GET.get('y_field', 'scrape.likes_count')

    # Fetch posts
    scrape_data = ScrapeData.objects.all()[:300]

    # Dictionary to store aggregated like counts per hashtag category
    category_likes = defaultdict(list)

    for scrape in scrape_data:
        hashtags = extract_hashtags(scrape.text)  # Extract hashtags from text
        matched_categories = set()

        for hashtag in hashtags:
            hashtag_lower = hashtag.lstrip("#").lower()  # Normalize hashtag
            if hashtag_lower in reversed_mapping:
                categories = reversed_mapping[hashtag_lower]
                for category, _ in categories.items():
                    matched_categories.add(category)

        for category in matched_categories:
            category_likes[category].append(scrape.likes_count)

    # Aggregate data: Calculate average likes per category
    aggregated_data = {
        category: sum(likes) / len(likes) if likes else 0
        for category, likes in category_likes.items()
    }

    # Prepare Plotly chart data
    if aggregated_data:
        fig = {
            "data": [{
                "x": list(aggregated_data.keys()),
                "y": list(aggregated_data.values()),
                "type": "bar",
                "hovertemplate": "Category: %{x}<br>Avg Likes: %{y}",
            }],
            "layout": {
                "title": "Average Likes by Hashtag Category",
                "xaxis": {"title": "Hashtag Category"},
                "yaxis": {"title": "Average Likes"},
                "template": "seaborn"
            }
        }
    else:
        fig = {"data": [], "layout": {}}

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(scrape_data),
    }

    return render(request, 'visualizer/chart_page.html', context)

#Grok
# def analyze_view(request):
#     data = load_mapping()

#     # Get selected fields from the GET request
#     x_field = request.GET.get('x_field', 'hashtag_groups')  # New default for hashtag groups
#     y_field = request.GET.get('y_field', 'scrape.likes_count')

#     # Split field into model and attribute (if applicable)
#     if '.' in x_field:
#         x_model, x_attr = x_field.split('.')
#     else:
#         x_model, x_attr = None, x_field  # For hashtag_groups
#     y_model, y_attr = y_field.split('.')

#     # Fetch data
#     scrape_data = ScrapeData.objects.all()[:300]
#     plot_data = []

#     for scrape in scrape_data:
#         try:
#             analyzer = AnalyzerResult.objects.get(img_name=scrape.img_name)
            
#             # Extract X value
#             if x_model == 'scrape':
#                 x_value = getattr(scrape, x_attr, None)
#             elif x_model == 'analyzer':
#                 if x_attr == 'polarity':
#                     sentiment_data = json.loads(analyzer.textstimmung)
#                     x_value = sentiment_data.get('polarity', 0)
#                 else:
#                     x_value = getattr(analyzer, x_attr, None)
#             elif x_attr == 'hashtag_groups':
#                 x_value = get_hashtag_groups(scrape.text, MAPPING)  # Get list of groups
#             else:
#                 x_value = None

#             # Extract Y value
#             if y_model == 'scrape':
#                 y_value = getattr(scrape, y_attr, None)
#             elif y_model == 'analyzer':
#                 if y_attr == 'polarity':
#                     sentiment_data = json.loads(analyzer.textstimmung)
#                     y_value = sentiment_data.get('polarity', 0)
#                 else:
#                     y_value = getattr(analyzer, y_attr, None)
#             else:
#                 y_value = None

#             if x_value is not None and y_value is not None:
#                 # If x_value is a list (e.g., hashtag groups), create an entry for each group
#                 if isinstance(x_value, list):
#                     for group in x_value:
#                         plot_data.append({
#                             'x': group,
#                             'y': y_value,
#                             'img_name': scrape.img_name
#                         })
#                 else:
#                     plot_data.append({
#                         'x': x_value,
#                         'y': y_value,
#                         'img_name': scrape.img_name
#                     })
#         except AnalyzerResult.DoesNotExist:
#             continue

#     # Aggregate data for hashtag groups if x_field is 'hashtag_groups'
#     if x_attr == 'hashtag_groups':
#         from collections import defaultdict
#         group_totals = defaultdict(float)
#         group_counts = defaultdict(int)
        
#         for item in plot_data:
#             group_totals[item['x']] += item['y']
#             group_counts[item['x']] += 1
        
#         # Calculate averages (or use totals, depending on your preference)
#         aggregated_data = [
#             {'x': group, 'y': group_totals[group] / group_counts[group]}
#             for group in group_totals
#         ]
#         plot_data = aggregated_data

#     # Determine data types
#     x_numeric = False
#     y_numeric = False
#     if plot_data:
#         x_numeric = is_numeric(plot_data[0]['x'])
#         y_numeric = is_numeric(plot_data[0]['y'])

#     # Generate Plotly figure
#     if plot_data:
#         if x_numeric and y_numeric:
#             # Scatter plot (unchanged)
#             fig = {
#                 'data': [{
#                     'x': [item['x'] for item in plot_data],
#                     'y': [item['y'] for item in plot_data],
#                     'type': 'scatter',
#                     'mode': 'markers',
#                     'hovertemplate': f'%{{customdata[0]}}<br>{x_field}: %{{x}}<br>{y_field}: %{{y}}'
#                 }],
#                 'layout': {
#                     'title': f'{y_field} vs {x_field}',
#                     'xaxis': {'title': x_field.replace(".", " ")},
#                     'yaxis': {'title': y_field.replace(".", " ")},
#                     'template': 'seaborn'
#                 }
#             }
#         elif not x_numeric and y_numeric:
#             # X non-numeric (e.g., hashtag groups), Y numeric: Bar plot
#             fig = {
#                 'data': [{
#                     'x': [item['x'] for item in plot_data],
#                     'y': [item['y'] for item in plot_data],
#                     'type': 'bar',
#                     'hovertemplate': f'{x_field}: %{{x}}<br>{y_field}: %{{y}}'
#                 }],
#                 'layout': {
#                     'title': f'Average {y_field} by {x_field}',
#                     'xaxis': {'title': x_field.replace(".", " ")},
#                     'yaxis': {'title': f'Average {y_field.replace(".", " ")}'},
#                     'template': 'seaborn'
#                 }
#             }
#         # Add other cases if needed (e.g., box plots)
#         else:
#             fig = {"data": [], "layout": {"title": "Unsupported chart type"}}
#         plot_json = json.dumps(fig)
#     else:
#         plot_json = json.dumps({"data": [], "layout": {}})

#     context = {
#         'plot_json': plot_json,
#         'data_count': len(plot_data),
#     }

#     return render(request, 'visualizer/chart_page.html', context)

def analyze_page(request):
    return render(request, 'visualizer/chart_page.html')

def get_hashtag_groups(text, mapping):
    """Extract hashtags from text and map them to their groups."""
    hashtags = re.findall(r'#\w+', text.lower())  # Extract hashtags (e.g., #G20 -> g20)
    groups = set()  # Use a set to avoid duplicates
    
    for hashtag in hashtags:
        hashtag = hashtag[1:]  # Remove the '#' symbol
        for group, clusters in mapping.items():
            for cluster, tags in clusters.items():
                if hashtag in tags:
                    groups.add(group)
                    break  # Move to next hashtag once a match is found
    return list(groups)  # Convert set back to list