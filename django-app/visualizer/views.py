import json
import requests

from django.shortcuts import render
from django.http import JsonResponse
from analyzer.models import AnalyzerResult
from scraper.models import ScrapeData

def is_numeric(value):
    """Helper function to check if a value is numeric."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def analyze_view(request):
    # Get selected fields from the GET request
    x_field = request.GET.get('x_field', 'analyzer.polarity')
    y_field = request.GET.get('y_field', 'scrape.likes_count')

    # Split field into model and attribute
    x_model, x_attr = x_field.split('.')
    y_model, y_attr = y_field.split('.')

    # Fetch data
    scrape_data = ScrapeData.objects.all()[:300]
    plot_data = []

    for scrape in scrape_data:
        try:
            analyzer = AnalyzerResult.objects.get(img_name=scrape.img_name)
            
            # Extract X value
            if x_model == 'scrape':
                x_value = getattr(scrape, x_attr, None)
            elif x_model == 'analyzer':
                if x_attr == 'polarity':
                    try:
                        sentiment_data = json.loads(analyzer.textstimmung)
                        x_value = sentiment_data.get('polarity', 0)
                    except (json.JSONDecodeError, TypeError):
                        x_value = 0
                else:
                    x_value = getattr(analyzer, x_attr, None)

            # Extract Y value
            if y_model == 'scrape':
                y_value = getattr(scrape, y_attr, None)
            elif y_model == 'analyzer':
                if y_attr == 'polarity':
                    try:
                        sentiment_data = json.loads(analyzer.textstimmung)
                        y_value = sentiment_data.get('polarity', 0)
                    except (json.JSONDecodeError, TypeError):
                        y_value = 0
                else:
                    y_value = getattr(analyzer, y_attr, None)

            if x_value is not None and y_value is not None:
                plot_data.append({
                    'x': x_value,
                    'y': y_value,
                    'img_name': scrape.img_name
                })
        except AnalyzerResult.DoesNotExist:
            continue

    # Determine data types (based on the first non-null value)
    x_numeric = False
    y_numeric = False
    if plot_data:
        x_numeric = is_numeric(plot_data[0]['x'])
        y_numeric = is_numeric(plot_data[0]['y'])

    # Generate Plotly figure based on data types
    if plot_data:
        if x_numeric and y_numeric:
            # Both numeric: Scatter plot
            fig = {
                'data': [{
                    'x': [item['x'] for item in plot_data],
                    'y': [item['y'] for item in plot_data],
                    'customdata': [[item['img_name']] for item in plot_data],
                    'type': 'scatter',
                    'mode': 'markers',
                    'hovertemplate': f'%{{customdata[0]}}<br>{x_field}: %{{x}}<br>{y_field}: %{{y}}'
                }],
                'layout': {
                    'title': f'{y_field} vs {x_field}',
                    'xaxis': {'title': x_field.replace(".", " ")},
                    'yaxis': {'title': y_field.replace(".", " ")},
                    'template': 'seaborn'
                }
            }
        elif x_numeric and not y_numeric:
            # X numeric, Y non-numeric: Box plot (Y categories, X values)
            fig = {
                'data': [{
                    'x': [item['y'] for item in plot_data],  # Categories on X
                    'y': [item['x'] for item in plot_data],  # Numeric on Y
                    'type': 'box',
                    'hovertemplate': f'Category: %{{x}}<br>{x_field}: %{{y}}'
                }],
                'layout': {
                    'title': f'{x_field} Distribution by {y_field}',
                    'xaxis': {'title': y_field.replace(".", " ")},
                    'yaxis': {'title': x_field.replace(".", " ")},
                    'template': 'seaborn'
                }
            }
        elif not x_numeric and y_numeric:
            # X non-numeric, Y numeric: Bar plot (X categories, Y values)
            categories = list(set(item['x'] for item in plot_data))
            y_values = [sum(item['y'] for item in plot_data if item['x'] == cat) / len([item for item in plot_data if item['x'] == cat]) for cat in categories]
            fig = {
                'data': [{
                    'x': categories,
                    'y': y_values,
                    'type': 'bar',
                    'hovertemplate': f'{x_field}: %{{x}}<br>{y_field}: %{{y}}'
                }],
                'layout': {
                    'title': f'{y_field} by {x_field}',
                    'xaxis': {'title': x_field.replace(".", " ")},
                    'yaxis': {'title': y_field.replace(".", " ")},
                    'template': 'seaborn'
                }
            }
        else:
            # Both non-numeric: Bar plot with counts of combinations
            from collections import Counter
            combinations = [(item['x'], item['y']) for item in plot_data]
            count_data = Counter(combinations)
            x_vals = [f"{x}-{y}" for (x, y) in count_data.keys()]
            y_vals = list(count_data.values())
            fig = {
                'data': [{
                    'x': x_vals,
                    'y': y_vals,
                    'type': 'bar',
                    'hovertemplate': f'{x_field}-{y_field}: %{{x}}<br>Count: %{{y}}'
                }],
                'layout': {
                    'title': f'Frequency of {x_field} and {y_field} Combinations',
                    'xaxis': {'title': f'{x_field}-{y_field} Combination'},
                    'yaxis': {'title': 'Count'},
                    'template': 'seaborn'
                }
            }
        plot_json = json.dumps(fig)
    else:
        plot_json = json.dumps({"data": [], "layout": {}})

    context = {
        'plot_json': plot_json,
        'data_count': len(plot_data),
    }

    return render(request, 'visualizer/chart_page.html', context)

def analyze_page(request):
    return render(request, 'visualizer/chart_page.html')