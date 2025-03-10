import json
import requests
import os
import re
import statistics
import math
import colorsys
import numpy as np
import matplotlib.colors as mcolors

from collections import defaultdict, Counter
from django.conf import settings

from django.shortcuts import render
from django.http import JsonResponse
from analyzer.models import AnalyzerResult
from scraper.models import ScrapeData
from django.db.models import Sum
from datetime import datetime
from plotly.subplots import make_subplots

from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from django.db.models.expressions import Func

# Load the mapping JSON file
MAPPING_FILE_PATH = os.path.join(settings.BASE_DIR, "data", "mapping_hashtag_cluster_group", "mapping.json")

# Enhanced Portal Mapping with Colors
PORTAL_MAPPING = {
    1383406462: {"name": "ZDF", "color": "#fa7d19"},  # Blue
    8537434: {"name": "Bild", "color": "#D00"},     # Orange
    1647208845: {"name": "SZ", "color": "#29293a"}     # Green
}
VALID_PORTAL_IDS = set(PORTAL_MAPPING.keys())

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

def sentiment_per_portal_over_time_view(request):
    """Visualize VADER and DeepSeek sentiment over time per portal"""
    # Fetch data, filtering by valid portals
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    ).order_by('taken_at_timestamp')
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_per_portal_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id and sentiment scores
    owner_id_map = {entry.img_name: entry.owner_id for entry in scrape_data}
    sentiment_dict = {}
    for entry in analyzer_data:
        vader_score = None
        deepseek_score = None
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, dict):
                vader_score = entry.sentiment_vader.get("score")
            elif isinstance(entry.sentiment_vader, str):
                try:
                    vader_data = json.loads(entry.sentiment_vader)
                    vader_score = vader_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if entry.sentiment_deepseek:
            if isinstance(entry.sentiment_deepseek, dict):
                deepseek_score = entry.sentiment_deepseek.get("score")
            elif isinstance(entry.sentiment_deepseek, str):
                try:
                    deepseek_data = json.loads(entry.sentiment_deepseek)
                    deepseek_score = deepseek_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if vader_score is not None or deepseek_score is not None:
            sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}

    # Collect data points by portal
    data_by_portal = {pid: {"vader_dates": [], "vader_scores": [], "deepseek_dates": [], "deepseek_scores": []} 
                      for pid in VALID_PORTAL_IDS}

    for entry in scrape_data:
        if entry.img_name in sentiment_dict:
            dt = datetime.fromtimestamp(entry.taken_at_timestamp)
            date_str = dt.strftime('%Y-%m-%d')
            portal_id = entry.owner_id
            sentiments = sentiment_dict[entry.img_name]
            
            if sentiments["vader"] is not None:
                data_by_portal[portal_id]["vader_dates"].append(date_str)
                data_by_portal[portal_id]["vader_scores"].append(sentiments["vader"])
            if sentiments["deepseek"] is not None:
                data_by_portal[portal_id]["deepseek_dates"].append(date_str)
                data_by_portal[portal_id]["deepseek_scores"].append(sentiments["deepseek"])

    # Prepare Plotly traces
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        portal_data = data_by_portal[portal_id]
        portal_name = PORTAL_MAPPING[portal_id]["name"]
        color = PORTAL_MAPPING[portal_id]["color"]

        # VADER trace
        if portal_data["vader_scores"]:
            vader_hover = [f"Date: {d}<br>Portal: {portal_name}<br>VADER Sentiment: {s:.2f}" 
                           for d, s in zip(portal_data["vader_dates"], portal_data["vader_scores"])]
            traces.append({
                "x": portal_data["vader_dates"],
                "y": portal_data["vader_scores"],
                "type": "scatter",
                "mode": "markers",
                "name": f"{portal_name} (VADER)",
                "marker": {"size": 8, "color": color},
                "text": vader_hover,
                "hovertemplate": "%{text}",
            })

        # DeepSeek trace
        if portal_data["deepseek_scores"]:
            deepseek_hover = [f"Date: {d}<br>Portal: {portal_name}<br>DeepSeek Sentiment: {s:.2f}" 
                              for d, s in zip(portal_data["deepseek_dates"], portal_data["deepseek_scores"])]
            traces.append({
                "x": portal_data["deepseek_dates"],
                "y": portal_data["deepseek_scores"],
                "type": "scatter",
                "mode": "markers",
                "name": f"{portal_name} (DeepSeek)",
                "marker": {"size": 8, "color": color},
                "text": deepseek_hover,
                "hovertemplate": "%{text}",
            })

    # Create Plotly chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Sentiment Over Time Per Portal",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Sentiment Score", "range": [-1, 1]},
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portal & Sentiment", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': sum(len(data_by_portal[pid]["vader_scores"]) + len(data_by_portal[pid]["deepseek_scores"]) 
                          for pid in VALID_PORTAL_IDS),
        'chart_type': 'sentiment_per_portal_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

def likes_per_portal_over_time_view(request):
    """Visualize total likes per portal (owner_id) over time"""
    # Fetch data, filtering only valid portal IDs
    scrape_data = ScrapeData.objects.filter(
        likes_count__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    ).order_by('taken_at_timestamp')

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'likes_per_portal_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Aggregate likes by date and portal
    likes_by_date = defaultdict(lambda: defaultdict(int))
    for entry in scrape_data:
        dt = datetime.fromtimestamp(entry.taken_at_timestamp)
        date_str = dt.strftime('%Y-%m-%d')
        likes_by_date[date_str][entry.owner_id] += entry.likes_count

    # Prepare data for Plotly
    dates = sorted(likes_by_date.keys())
    traces = []
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Colors for ZDF, Bild, SZ

    # Example update for likes_per_portal_over_time_view
    for i, portal_id in enumerate(VALID_PORTAL_IDS):
        counts = [likes_by_date[date].get(portal_id, 0) for date in dates]
        portal_name = PORTAL_MAPPING[portal_id]["name"]
        color = PORTAL_MAPPING[portal_id]["color"]
        hover_texts = [f"Date: {d}<br>Portal: {portal_name}<br>Likes: {c}" for d, c in zip(dates, counts)]
        traces.append({
            "x": dates,
            "y": counts,
            "type": "scatter",
            "mode": "lines+markers",
            "name": portal_name,
            "line": {"color": color, "width": 2},
            "marker": {"size": 6, "color": color},
            "text": hover_texts,
            "hovertemplate": "%{text}",
        })

    # Create Plotly line chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Likes Per Portal Over Time",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Total Likes"},
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portals", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(dates),
        'chart_type': 'likes_per_portal_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

def hashtag_group_usage_view(request):
    """Visualize total usage of hashtag groups, stacked by portal"""
    # Fetch data, filtering by valid portals
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count group occurrences by portal
    group_counts_by_portal = {pid: Counter() for pid in VALID_PORTAL_IDS}
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        group_counts_by_portal[entry.owner_id].update(unique_groups)

    # Get all unique groups
    all_groups = sorted(set().union(*[set(c.keys()) for c in group_counts_by_portal.values()]))

    # Prepare Plotly traces (one per portal)
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        counts = [group_counts_by_portal[portal_id].get(group, 0) for group in all_groups]
        portal_name = PORTAL_MAPPING[portal_id]["name"]
        color = PORTAL_MAPPING[portal_id]["color"]
        hover_texts = [f"Group: {g}<br>Portal: {portal_name}<br>Count: {c}" for g, c in zip(all_groups, counts)]
        traces.append({
            "x": all_groups,
            "y": counts,
            "type": "bar",
            "name": portal_name,
            "marker": {"color": color},
            "text": hover_texts,
            "hovertemplate": "%{text}",
        })

    # Create Plotly stacked bar chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Total Usage of Hashtag Groups by Portal",
            "xaxis": {
                "title": "Hashtag Group",
                "tickangle": -45,  # Rotate labels
                "automargin": True,  # Auto-adjust margins for long labels
                "tickfont": {"size": 10},  # Smaller font for readability
            },
            "yaxis": {"title": "Number of Posts"},
            "template": "seaborn",
            "hovermode": "closest",
            "barmode": "stack",  # Stack bars
            "legend": {"title": "Portals", "x": 1, "y": 1},
            "margin": {"b": 150}  # Increase bottom margin for long labels
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': sum(sum(c.values()) for c in group_counts_by_portal.values()),
        'chart_type': 'hashtag_group_usage'
    }
    return render(request, 'visualizer/chart_page.html', context)

def hashtag_group_percentage_view(request):
    """Visualize percentage usage of hashtag groups as a donut chart"""
    # Fetch data, filtering by valid portals
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_percentage'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count group occurrences
    group_counts = Counter()
    total_posts = scrape_data.count()
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        group_counts.update(unique_groups)

    # Calculate percentages
    groups = list(group_counts.keys())
    counts = [group_counts[group] for group in groups]
    percentages = [count / total_posts * 100 for count in counts]
    hover_texts = [f"Group: {g}<br>Percentage: {p:.1f}%<br>Count: {c}" for g, p, c in zip(groups, percentages, counts)]

    # Use a color scale for variety (since not portal-specific)
    import plotly.express as px
    colors = px.colors.qualitative.Plotly[:len(groups)]

    # Create Plotly donut chart
    fig = {
        "data": [{
            "labels": groups,
            "values": percentages,
            "type": "pie",
            "hole": 0.4,  # Makes it a donut chart
            "marker": {"colors": colors},
            "text": [f"{p:.1f}%" for p in percentages],
            "hovertemplate": "%{text}",
            "textinfo": "label+percent",
            "textposition": "inside",
        }],
        "layout": {
            "title": "Percentage Usage of Hashtag Groups",
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Hashtag Groups", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': total_posts,
        'chart_type': 'hashtag_group_percentage'
    }
    return render(request, 'visualizer/chart_page.html', context)

def avg_likes_per_hashtag_group_view(request):
    """Visualize average likes per hashtag group"""
    # Fetch data, filtering by valid portals
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        likes_count__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'avg_likes_per_hashtag_group'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Aggregate likes by group
    likes_by_group = defaultdict(list)
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        for group in unique_groups:
            likes_by_group[group].append(entry.likes_count)

    # Calculate average likes per group
    groups = list(likes_by_group.keys())
    avg_likes = [statistics.mean(likes_by_group[group]) for group in groups]
    hover_texts = [f"Group: {g}<br>Avg Likes: {a:.1f}<br>Posts: {len(likes_by_group[g])}" for g, a in zip(groups, avg_likes)]

    # Create Plotly bar chart
    fig = {
        "data": [{
            "x": groups,
            "y": avg_likes,
            "type": "bar",
            "marker": {"color": "#722222"},  # Nice looking red
            "text": [f"{a:.1f}" for a in avg_likes],
            "textposition": "auto",
            "hovertemplate": "%{text}",
        }],
        "layout": {
            "title": "Average Likes Per Hashtag Group",
            "xaxis": {
                "title": "Hashtag Group",
                "tickangle": -45,
                "automargin": True,
                "tickfont": {"size": 10},
            },
            "yaxis": {"title": "Average Likes"},
            "template": "seaborn",
            "hovermode": "closest",
            "margin": {"b": 150}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': scrape_data.count(),
        'chart_type': 'avg_likes_per_hashtag_group'
    }
    return render(request, 'visualizer/chart_page.html', context)

def comment_count_per_hashtag_group_view(request):
    """Visualize total comment count per hashtag group, stacked by portal"""
    # Fetch data, filtering by valid portals
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        comment_count__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'comment_count_per_hashtag_group'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count comments by group and portal
    comment_counts_by_portal = {pid: Counter() for pid in VALID_PORTAL_IDS}
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        for group in unique_groups:
            comment_counts_by_portal[entry.owner_id][group] += entry.comment_count

    # Get all unique groups
    all_groups = sorted(set().union(*[set(c.keys()) for c in comment_counts_by_portal.values()]))

    # Prepare Plotly traces
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        counts = [comment_counts_by_portal[portal_id].get(group, 0) for group in all_groups]
        portal_name = PORTAL_MAPPING[portal_id]["name"]
        color = PORTAL_MAPPING[portal_id]["color"]
        hover_texts = [f"Group: {g}<br>Portal: {portal_name}<br>Comments: {c}" for g, c in zip(all_groups, counts)]
        traces.append({
            "x": all_groups,
            "y": counts,
            "type": "bar",
            "name": portal_name,
            "marker": {"color": color},
            "text": hover_texts,
            "hovertemplate": "%{text}",
        })

    # Create Plotly stacked bar chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Total Comment Count Per Hashtag Group by Portal",
            "xaxis": {
                "title": "Hashtag Group",
                "tickangle": -45,
                "automargin": True,
                "tickfont": {"size": 10},
            },
            "yaxis": {"title": "Total Comments"},
            "template": "seaborn",
            "hovermode": "closest",
            "barmode": "stack",
            "legend": {"title": "Portals", "x": 1, "y": 1},
            "margin": {"b": 150}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': scrape_data.count(),
        'chart_type': 'comment_count_per_hashtag_group'
    }
    return render(request, 'visualizer/chart_page.html', context)

def sentiment_radial_view(request):
    """Radial bar chart of VADER and DeepSeek sentiment distribution for ZDF, excluding 0.0"""
    # Fetch data for ZDF only (owner_id = 1383406462)
    portal_id = 1383406462  # ZDF
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id=portal_id
    )
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to sentiment scores (VADER and DeepSeek)
    sentiment_dict = {}
    for entry in analyzer_data:
        vader_score = None
        deepseek_score = None
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, dict):
                vader_score = entry.sentiment_vader.get("score")
            elif isinstance(entry.sentiment_vader, str):
                try:
                    vader_data = json.loads(entry.sentiment_vader)
                    vader_score = vader_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if entry.sentiment_deepseek:
            if isinstance(entry.sentiment_deepseek, dict):
                deepseek_score = entry.sentiment_deepseek.get("score")
            elif isinstance(entry.sentiment_deepseek, str):
                try:
                    deepseek_data = json.loads(entry.sentiment_deepseek)
                    deepseek_score = deepseek_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        # Only include if at least one non-zero score exists
        if (vader_score is not None and vader_score != 0.0) or (deepseek_score is not None and deepseek_score != 0.0):
            sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}

    # Collect sentiment scores for ZDF, excluding 0.0
    vader_scores = []
    deepseek_scores = []
    for entry in scrape_data:
        if entry.img_name in sentiment_dict:
            scores = sentiment_dict[entry.img_name]
            if scores["vader"] is not None and scores["vader"] != 0.0:
                vader_scores.append(scores["vader"])
            if scores["deepseek"] is not None and scores["deepseek"] != 0.0:
                deepseek_scores.append(scores["deepseek"])

    if not (vader_scores or deepseek_scores):
        fig = {"data": [], "layout": {"title": "No Non-Zero Sentiment Data for ZDF"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Define sentiment bins from 1 to -1 with 0.2 steps, excluding 0.0
    sentiment_bins = [round(1 - i * 0.2, 1) for i in range(5)] + [round(-0.8 + i * 0.2, 1) for i in range(5)]  # [1, 0.8, ..., 0.2, -0.8, ..., -1]
    
    # Bin VADER scores
    vader_bin_counts = [0] * len(sentiment_bins)
    for score in vader_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        vader_bin_counts[closest_bin_idx] += 1

    # Bin DeepSeek scores
    deepseek_bin_counts = [0] * len(sentiment_bins)
    for score in deepseek_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        deepseek_bin_counts[closest_bin_idx] += 1

    # Map bins to angles (0° = 1, 180° = 0.2, 360° = -1)
    theta = [i * (360 / len(sentiment_bins)) for i in range(len(sentiment_bins))]  # 10 bins, 36° each
    theta_adjusted = [t + 36 for t in theta]  # Shift so 0.2 is at 180°

    # Hover texts
    vader_hover = [f"Sentiment: {s}<br>VADER Count: {c}" for s, c in zip(sentiment_bins, vader_bin_counts)]
    deepseek_hover = [f"Sentiment: {s}<br>DeepSeek Count: {c}" for s, c in zip(sentiment_bins, deepseek_bin_counts)]

    # Create Plotly radial bar chart with two datasets
    fig = {
        "data": [
            {
                "r": vader_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "VADER",
                "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # Solid ZDF blue
                "text": vader_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.8
            },
            {
                "r": deepseek_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "DeepSeek",
                "marker": {
                    "color": "#66b3ff",  # Lighter blue for DeepSeek
                    "line": {"width": 1, "color": "#000000"}  # Black outline for contrast
                },
                "text": deepseek_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.6
            }
        ],
        "layout": {
            "title": f"VADER and DeepSeek Sentiment Distribution for {PORTAL_MAPPING[portal_id]['name']} (Non-Zero)",
            "polar": {
                "radialaxis": {"title": "Count of Posts"},
                "angularaxis": {
                    "title": "Sentiment Score",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": [36, 72, 108, 144, 180, 216, 252, 288, 324, 360],
                    "ticktext": ["1", "0.8", "0.6", "0.4", "0.2", "-0.8", "-0.6", "-0.4", "-0.2", "-1"]
                }
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Sentiment Type", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(vader_scores) + len(deepseek_scores),
        'chart_type': 'sentiment_radial'
    }
    return render(request, 'visualizer/chart_page.html', context)

def sentiment_radial_bild_view(request):
    """Radial bar chart of VADER and DeepSeek sentiment distribution for Bild, excluding 0.0"""
    # Fetch data for Bild only (owner_id = 8537434)
    portal_id = 8537434  # Bild
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id=portal_id
    )
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial_bild'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to sentiment scores (VADER and DeepSeek)
    sentiment_dict = {}
    for entry in analyzer_data:
        vader_score = None
        deepseek_score = None
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, dict):
                vader_score = entry.sentiment_vader.get("score")
            elif isinstance(entry.sentiment_vader, str):
                try:
                    vader_data = json.loads(entry.sentiment_vader)
                    vader_score = vader_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if entry.sentiment_deepseek:
            if isinstance(entry.sentiment_deepseek, dict):
                deepseek_score = entry.sentiment_deepseek.get("score")
            elif isinstance(entry.sentiment_deepseek, str):
                try:
                    deepseek_data = json.loads(entry.sentiment_deepseek)
                    deepseek_score = deepseek_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if (vader_score is not None and vader_score != 0.0) or (deepseek_score is not None and deepseek_score != 0.0):
            sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}

    # Collect sentiment scores for Bild, excluding 0.0
    vader_scores = []
    deepseek_scores = []
    for entry in scrape_data:
        if entry.img_name in sentiment_dict:
            scores = sentiment_dict[entry.img_name]
            if scores["vader"] is not None and scores["vader"] != 0.0:
                vader_scores.append(scores["vader"])
            if scores["deepseek"] is not None and scores["deepseek"] != 0.0:
                deepseek_scores.append(scores["deepseek"])

    if not (vader_scores or deepseek_scores):
        fig = {"data": [], "layout": {"title": "No Non-Zero Sentiment Data for Bild"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial_bild'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Define sentiment bins from 1 to -1 with 0.2 steps, excluding 0.0
    sentiment_bins = [round(1 - i * 0.2, 1) for i in range(5)] + [round(-0.8 + i * 0.2, 1) for i in range(5)]  # [1, 0.8, ..., 0.2, -0.8, ..., -1]
    
    # Bin VADER scores
    vader_bin_counts = [0] * len(sentiment_bins)
    for score in vader_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        vader_bin_counts[closest_bin_idx] += 1

    # Bin DeepSeek scores
    deepseek_bin_counts = [0] * len(sentiment_bins)
    for score in deepseek_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        deepseek_bin_counts[closest_bin_idx] += 1

    # Map bins to angles (0° = 1, 180° = 0.2, 360° = -1)
    theta = [i * (360 / len(sentiment_bins)) for i in range(len(sentiment_bins))]  # 10 bins, 36° each
    theta_adjusted = [t + 36 for t in theta]  # Shift so 0.2 is at 180°

    # Hover texts
    vader_hover = [f"Sentiment: {s}<br>VADER Count: {c}" for s, c in zip(sentiment_bins, vader_bin_counts)]
    deepseek_hover = [f"Sentiment: {s}<br>DeepSeek Count: {c}" for s, c in zip(sentiment_bins, deepseek_bin_counts)]

    # Create Plotly radial bar chart with two datasets
    fig = {
        "data": [
            {
                "r": vader_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "VADER",
                "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # Bild orange
                "text": vader_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.8
            },
            {
                "r": deepseek_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "DeepSeek",
                "marker": {
                    "color": "#ffbf80",  # Lighter orange for DeepSeek
                    "line": {"width": 1, "color": "#000000"}  # Black outline
                },
                "text": deepseek_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.6
            }
        ],
        "layout": {
            "title": f"VADER and DeepSeek Sentiment Distribution for {PORTAL_MAPPING[portal_id]['name']} (Non-Zero)",
            "polar": {
                "radialaxis": {"title": "Count of Posts"},
                "angularaxis": {
                    "title": "Sentiment Score",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": [36, 72, 108, 144, 180, 216, 252, 288, 324, 360],
                    "ticktext": ["1", "0.8", "0.6", "0.4", "0.2", "-0.8", "-0.6", "-0.4", "-0.2", "-1"]
                }
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Sentiment Type", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(vader_scores) + len(deepseek_scores),
        'chart_type': 'sentiment_radial_bild'
    }
    return render(request, 'visualizer/chart_page.html', context)

def sentiment_radial_sz_view(request):
    """Radial bar chart of VADER and DeepSeek sentiment distribution for SZ, excluding 0.0"""
    # Fetch data for SZ only (owner_id = 1647208845)
    portal_id = 1647208845  # SZ
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id=portal_id
    )
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial_sz'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to sentiment scores (VADER and DeepSeek)
    sentiment_dict = {}
    for entry in analyzer_data:
        vader_score = None
        deepseek_score = None
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, dict):
                vader_score = entry.sentiment_vader.get("score")
            elif isinstance(entry.sentiment_vader, str):
                try:
                    vader_data = json.loads(entry.sentiment_vader)
                    vader_score = vader_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if entry.sentiment_deepseek:
            if isinstance(entry.sentiment_deepseek, dict):
                deepseek_score = entry.sentiment_deepseek.get("score")
            elif isinstance(entry.sentiment_deepseek, str):
                try:
                    deepseek_data = json.loads(entry.sentiment_deepseek)
                    deepseek_score = deepseek_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if (vader_score is not None and vader_score != 0.0) or (deepseek_score is not None and deepseek_score != 0.0):
            sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}

    # Collect sentiment scores for SZ, excluding 0.0
    vader_scores = []
    deepseek_scores = []
    for entry in scrape_data:
        if entry.img_name in sentiment_dict:
            scores = sentiment_dict[entry.img_name]
            if scores["vader"] is not None and scores["vader"] != 0.0:
                vader_scores.append(scores["vader"])
            if scores["deepseek"] is not None and scores["deepseek"] != 0.0:
                deepseek_scores.append(scores["deepseek"])

    if not (vader_scores or deepseek_scores):
        fig = {"data": [], "layout": {"title": "No Non-Zero Sentiment Data for SZ"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_radial_sz'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Define sentiment bins from 1 to -1 with 0.2 steps, excluding 0.0
    sentiment_bins = [round(1 - i * 0.2, 1) for i in range(5)] + [round(-0.8 + i * 0.2, 1) for i in range(5)]  # [1, 0.8, ..., 0.2, -0.8, ..., -1]
    
    # Bin VADER scores
    vader_bin_counts = [0] * len(sentiment_bins)
    for score in vader_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        vader_bin_counts[closest_bin_idx] += 1

    # Bin DeepSeek scores
    deepseek_bin_counts = [0] * len(sentiment_bins)
    for score in deepseek_scores:
        closest_bin_idx = min(range(len(sentiment_bins)), key=lambda i: abs(sentiment_bins[i] - score))
        deepseek_bin_counts[closest_bin_idx] += 1

    # Map bins to angles (0° = 1, 180° = 0.2, 360° = -1)
    theta = [i * (360 / len(sentiment_bins)) for i in range(len(sentiment_bins))]  # 10 bins, 36° each
    theta_adjusted = [t + 36 for t in theta]  # Shift so 0.2 is at 180°

    # Hover texts
    vader_hover = [f"Sentiment: {s}<br>VADER Count: {c}" for s, c in zip(sentiment_bins, vader_bin_counts)]
    deepseek_hover = [f"Sentiment: {s}<br>DeepSeek Count: {c}" for s, c in zip(sentiment_bins, deepseek_bin_counts)]

    # Create Plotly radial bar chart with two datasets
    fig = {
        "data": [
            {
                "r": vader_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "VADER",
                "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # SZ green
                "text": vader_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.8
            },
            {
                "r": deepseek_bin_counts,
                "theta": theta_adjusted,
                "type": "barpolar",
                "name": "DeepSeek",
                "marker": {
                    "color": "#85e085",  # Lighter green for DeepSeek
                    "line": {"width": 1, "color": "#000000"}  # Black outline
                },
                "text": deepseek_hover,
                "hovertemplate": "%{text}",
                "opacity": 0.6
            }
        ],
        "layout": {
            "title": f"VADER and DeepSeek Sentiment Distribution for {PORTAL_MAPPING[portal_id]['name']} (Non-Zero)",
            "polar": {
                "radialaxis": {"title": "Count of Posts"},
                "angularaxis": {
                    "title": "Sentiment Score",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": [36, 72, 108, 144, 180, 216, 252, 288, 324, 360],
                    "ticktext": ["1", "0.8", "0.6", "0.4", "0.2", "-0.8", "-0.6", "-0.4", "-0.2", "-1"]
                }
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Sentiment Type", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(vader_scores) + len(deepseek_scores),
        'chart_type': 'sentiment_radial_sz'
    }
    return render(request, 'visualizer/chart_page.html', context)

def top_hashtags_over_time_view(request):
    """Visualize the top 10 hashtags over time"""
    # Load hashtag data
    scrape_data = ScrapeData.objects.filter(extracted_hashtags__isnull=False).order_by('taken_at_timestamp')

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'top_hashtags_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Step 1: Count total occurrences of each hashtag to find top 10
    hashtag_totals = Counter()
    for entry in scrape_data:
        if entry.extracted_hashtags:
            hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
            hashtag_totals.update([tag.lower() for tag in hashtags])  # Lowercase for consistency

    # Get the top 10 hashtags
    top_10_hashtags = [hashtag for hashtag, _ in hashtag_totals.most_common(10)]
    print(f"Top 10 hashtags: {top_10_hashtags}")

    # Step 2: Aggregate hashtag counts by date
    hashtag_by_date = defaultdict(lambda: defaultdict(int))
    for entry in scrape_data:
        dt = datetime.fromtimestamp(entry.taken_at_timestamp)
        date_str = dt.strftime('%Y-%m-%d')
        if entry.extracted_hashtags:
            hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
            for tag in hashtags:
                tag = tag.lower()
                if tag in top_10_hashtags:
                    hashtag_by_date[date_str][tag] += 1

    # Step 3: Prepare data for Plotly
    dates = sorted(hashtag_by_date.keys())
    traces = []
    for hashtag in top_10_hashtags:
        counts = [hashtag_by_date[date].get(hashtag, 0) for date in dates]
        hover_texts = [f"Date: {d}<br>Hashtag: #{hashtag}<br>Count: {c}" for d, c in zip(dates, counts)]
        traces.append({
            "x": dates,
            "y": counts,
            "type": "scatter",
            "mode": "lines",
            "name": f"#{hashtag}",
            "stackgroup": "one",  # Stacks the areas
            "line": {"width": 1},
            "text": hover_texts,
            "hovertemplate": "%{text}",
        })

    # Create Plotly stacked area chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Top 10 Hashtags Over Time",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Hashtag Count"},
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Hashtags", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(dates),
        'chart_type': 'top_hashtags_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

def dominant_background_colors_view(request):
    """Visualize the top 10 dominant background colors per portal"""
    # Fetch data from AnalyzerResult and ScrapeData
    analyzer_results = AnalyzerResult.objects.filter(background_color__isnull=False)
    scrape_data = ScrapeData.objects.filter(img_name__in=[result.image_name for result in analyzer_results])

    # Map image names to portals (owner_id)
    image_to_portal = {data.img_name: data.owner_id for data in scrape_data}

    # Group background colors by portal
    portal_background_colors = defaultdict(list)
    for result in analyzer_results:
        if result.image_name in image_to_portal:
            portal_id = image_to_portal[result.image_name]
            portal_background_colors[portal_id].append(result.background_color)

    # Count the top 10 background colors for each portal
    portal_color_data = []
    for portal_id, colors in portal_background_colors.items():
        if portal_id in PORTAL_MAPPING:
            portal_name = PORTAL_MAPPING[portal_id]['name']
            color_counts = Counter(colors)
            top_10_colors = color_counts.most_common(10)  # Get the top 10 colors
            for color, count in top_10_colors:
                portal_color_data.append({
                    'portal': portal_name,
                    'color': color,
                    'count': count
                })

    # Sort data by portal and then by count (descending)
    portal_color_data.sort(key=lambda x: (x['portal'], -x['count']))

    # Create a Plotly bar chart
    fig = {
        "data": [
            {
                "x": [entry['portal'] for entry in portal_color_data],  # Group by portal
                "y": [entry['count'] for entry in portal_color_data],  # Count of each color
                "type": "bar",
                "marker": {"color": [entry['color'] for entry in portal_color_data]},  # Color bars by background color
                "name": "Background Colors",
                "hovertext": [f"Color: {entry['color']}<br>Count: {entry['count']}" for entry in portal_color_data],
                "hovertemplate": "%{hovertext}<extra></extra>"
            }
        ],
        "layout": {
            "title": "Top 10 Dominant Background Colors per Portal",
            "xaxis": {"title": "Portal", "categoryorder": "category ascending"},  # Sort portals alphabetically
            "yaxis": {"title": "Count"},
            "barmode": "group",
            "showlegend": False
        }
    }

    # Convert the chart to JSON
    plot_json = json.dumps(fig)

    # Pass the chart to the template
    context = {
        'plot_json': plot_json,
        'chart_type': 'dominant_background_colors'
    }
    return render(request, 'visualizer/chart_page.html', context)

def text_space_usage_view(request):
    """Visualize average percentage of text space usage per portal"""
    # Fetch data from AnalyzerResult and ScrapeData
    analyzer_results = AnalyzerResult.objects.filter(bounding_boxes__isnull=False)
    scrape_data = ScrapeData.objects.filter(img_name__in=[result.image_name for result in analyzer_results])

    # Map image names to portals (owner_id) and image dimensions
    image_to_portal = {}
    image_to_dimensions = {}
    for data in scrape_data:
        image_to_portal[data.img_name] = data.owner_id
        image_to_dimensions[data.img_name] = (data.display_height, data.display_width)

    # Calculate text space usage for each image
    portal_space_data = defaultdict(lambda: {'total_text_area': 0, 'total_image_area': 0, 'count': 0})
    for result in analyzer_results:
        if result.image_name in image_to_portal and result.image_name in image_to_dimensions:
            portal_id = image_to_portal[result.image_name]
            height, width = image_to_dimensions[result.image_name]
            total_image_area = height * width

            # Parse bounding_boxes (assuming it's a JSON list of {"text": "...", "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]})
            bounding_boxes = json.loads(result.bounding_boxes)
            total_text_area = 0
            for box in bounding_boxes:
                bbox = box['bbox']  # Get the bounding box coordinates
                # Extract the four corner points
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                # Calculate width and height of the bounding box
                box_width = max(x_coords) - min(x_coords)
                box_height = max(y_coords) - min(y_coords)
                # Calculate area of the bounding box
                total_text_area += box_width * box_height

            # Update portal data
            portal_space_data[portal_id]['total_text_area'] += total_text_area
            portal_space_data[portal_id]['total_image_area'] += total_image_area
            portal_space_data[portal_id]['count'] += 1

    # Calculate average percentage of text space usage for each portal
    portal_avg_data = []
    for portal_id, data in portal_space_data.items():
        if portal_id in PORTAL_MAPPING:
            portal_name = PORTAL_MAPPING[portal_id]['name']
            portal_color = PORTAL_MAPPING[portal_id]['color']
            avg_proportion = (data['total_text_area'] / data['total_image_area']) * 100  # As percentage

            portal_avg_data.append({
                'portal': portal_name,
                'avg_proportion': avg_proportion,
                'color': portal_color
            })

    # Sort data by portal name
    portal_avg_data.sort(key=lambda x: x['portal'])

    # Create a Plotly bar chart
    fig = {
        "data": [
            {
                "x": [entry['portal'] for entry in portal_avg_data],
                "y": [entry['avg_proportion'] for entry in portal_avg_data],
                "type": "bar",
                "marker": {"color": [entry['color'] for entry in portal_avg_data]},  # Use portal colors
                "name": "Average Text Space Usage (%)",
                "hovertext": [f"Portal: {entry['portal']}<br>Avg Text Space: {entry['avg_proportion']:.2f}%" for entry in portal_avg_data],
                "hovertemplate": "%{hovertext}<extra></extra>"
            }
        ],
        "layout": {
            "title": "Average Percentage of Text Space Usage per Portal",
            "xaxis": {"title": "Portal", "categoryorder": "category ascending"},
            "yaxis": {"title": "Average Text Space Usage (%)"},
            "showlegend": False
        }
    }

    # Convert the chart to JSON
    plot_json = json.dumps(fig)

    # Pass the chart to the template
    context = {
        'plot_json': plot_json,
        'chart_type': 'text_space_usage'
    }
    return render(request, 'visualizer/chart_page.html', context)

def background_color_radial_view(request, portal_id):
    """Radial bar chart of background color distribution for a specific portal"""
    # Validate portal_id
    if portal_id not in PORTAL_MAPPING:
        fig = {"data": [], "layout": {"title": "Invalid Portal ID"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'background_color_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Fetch data for the specified portal
    scrape_data = ScrapeData.objects.filter(owner_id=portal_id)
    analyzer_data = AnalyzerResult.objects.filter(image_name__in=[data.img_name for data in scrape_data], background_color__isnull=False)

    if not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'background_color_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Count occurrences of each background color
    color_counts = Counter()
    for entry in analyzer_data:
        color = entry.background_color
        if color and color.startswith("#") and len(color) == 7:  # Ensure valid hex color
            color_counts[color] += 1

    if not color_counts:
        fig = {"data": [], "layout": {"title": "No Valid Background Colors Found"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'background_color_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Prepare data for Plotly
    colors = list(color_counts.keys())
    counts = list(color_counts.values())

    # Map colors to angles (0° to 360°)
    angle_step = 360 / len(colors)  # Equal spacing for each color
    angles = [i * angle_step for i in range(len(colors))]

    # Hover texts
    hover_texts = [f"Color: {color}<br>Count: {count}" for color, count in zip(colors, counts)]

    # Create Plotly radial bar chart
    fig = {
        "data": [
            {
                "r": counts,
                "theta": angles,
                "type": "barpolar",
                "name": "Background Colors",
                "marker": {"color": colors},  # Use the actual colors for the bars
                "text": hover_texts,
                "hovertemplate": "%{text}",
                "opacity": 0.8
            }
        ],
        "layout": {
            "title": f"Background Color Distribution for {PORTAL_MAPPING[portal_id]['name']}",
            "polar": {
                "radialaxis": {"title": "Count of Posts", "visible": True},
                "angularaxis": {
                    "title": "Color",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": angles,  # Use the calculated angles
                    "ticktext": colors,  # Use the actual colors as labels
                    "rotation": 90  # Rotate labels for better readability
                }
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Colors", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(analyzer_data),
        'chart_type': 'background_color_radial'
    }
    return render(request, 'visualizer/chart_page.html', context)

def text_color_usage_radial_view(request):
    """Radial bar chart of text color usage frequency across all bounding boxes"""
    # Fetch data
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        text_colors__isnull=False,
        bounding_boxes__isnull=False
    )

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_color_usage_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id
    image_to_owner = {entry.img_name: entry.owner_id for entry in scrape_data}

    # Count colors per portal
    color_counts_by_portal = {pid: Counter() for pid in VALID_PORTAL_IDS}
    for entry in analyzer_data:
        if entry.image_name in image_to_owner:
            portal_id = image_to_owner[entry.image_name]
            colors = json.loads(entry.text_colors) if isinstance(entry.text_colors, str) else entry.text_colors
            boxes = json.loads(entry.bounding_boxes) if isinstance(entry.bounding_boxes, str) else entry.bounding_boxes
            if len(colors) != len(boxes):
                continue  # Skip if mismatch
            for color in colors:
                color_counts_by_portal[portal_id][color.lower()] += 1

    # Get all unique colors
    all_colors = set().union(*[set(c.keys()) for c in color_counts_by_portal.values()])
    if not all_colors:
        fig = {"data": [], "layout": {"title": "No Text Colors Found"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_color_usage_radial'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Map colors to angles based on hue
    def hex_to_hue(hex_color):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        h, _, _ = colorsys.rgb_to_hsv(*rgb)
        return h * 360  # Hue in degrees (0-360)

    color_angles = {color: hex_to_hue(color) for color in all_colors}
    sorted_colors = sorted(all_colors, key=lambda c: color_angles[c])

    # Prepare traces for each portal
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        counts = [color_counts_by_portal[portal_id].get(color, 0) for color in sorted_colors]
        hover_texts = [f"Color: {c}<br>Portal: {PORTAL_MAPPING[portal_id]['name']}<br>Count: {cnt}" 
                       for c, cnt in zip(sorted_colors, counts)]
        traces.append({
            "r": counts,
            "theta": [color_angles[c] for c in sorted_colors],
            "type": "barpolar",
            "name": PORTAL_MAPPING[portal_id]["name"],
            "marker": {
                "color": sorted_colors,  # Bars use the actual text colors
                "line": {"width": 1, "color": PORTAL_MAPPING[portal_id]["color"]}  # Outline in portal color
            },
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.7
        })

    # Create Plotly radial bar chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Text Color Usage Frequency Across Bounding Boxes",
            "polar": {
                "radialaxis": {"title": "Count of Uses"},
                "angularaxis": {
                    "title": "Color (Hue)",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": [0, 60, 120, 180, 240, 300, 360],
                    "ticktext": ["Red", "Yellow", "Green", "Cyan", "Blue", "Magenta", "Red"]
                }
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portals", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': sum(sum(c.values()) for c in color_counts_by_portal.values()),
        'chart_type': 'text_color_usage_radial'
    }
    return render(request, 'visualizer/chart_page.html', context)

def text_color_usage_bar_view(request):
    """Stacked horizontal bar chart of text color usage frequency across bounding boxes"""
    # Fetch data
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        text_colors__isnull=False,
        bounding_boxes__isnull=False
    )

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_color_usage_bar'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id
    image_to_owner = {entry.img_name: entry.owner_id for entry in scrape_data}

    # Count colors per portal
    color_counts_by_portal = {pid: Counter() for pid in VALID_PORTAL_IDS}
    for entry in analyzer_data:
        if entry.image_name in image_to_owner:
            portal_id = image_to_owner[entry.image_name]
            colors = json.loads(entry.text_colors) if isinstance(entry.text_colors, str) else entry.text_colors
            boxes = json.loads(entry.bounding_boxes) if isinstance(entry.bounding_boxes, str) else entry.bounding_boxes
            if len(colors) != len(boxes):
                continue  # Skip if mismatch
            for color in colors:
                color_counts_by_portal[portal_id][color.lower()] += 1

    # Get all unique colors and total counts
    total_counts = Counter()
    for counter in color_counts_by_portal.values():
        total_counts.update(counter)
    if not total_counts:
        fig = {"data": [], "layout": {"title": "No Text Colors Found"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_color_usage_bar'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Sort colors by total frequency (top 20 for readability)
    top_colors = [color for color, _ in total_counts.most_common(5)]
    # top_colors.reverse()

    # Prepare traces for each portal
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        counts = [color_counts_by_portal[portal_id].get(color, 0) for color in top_colors]
        hover_texts = [f"Color: {c}<br>Portal: {PORTAL_MAPPING[portal_id]['name']}<br>Count: {cnt}" 
                       for c, cnt in zip(top_colors, counts)]
        traces.append({
            "x": counts,
            "y": top_colors,
            "type": "bar",
            "name": PORTAL_MAPPING[portal_id]["name"],
            "orientation": "h",
            # "width" : 0.25,
            "marker": {
                "color": top_colors,  # Bars use the actual text colors
                "line": {"width": 2, "color": PORTAL_MAPPING[portal_id]["color"]}  # Outline in portal color
            },
            "text":  [f"{cnt}" for c, cnt in zip(top_colors, counts)],
            "hovertemplate": hover_texts,
            "opacity": 0.8
        })

    # Create Plotly stacked bar chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Text Color Usage Frequency Across Bounding Boxes (Top 5)",
            "xaxis": {
                "title": "Number of Uses (Log Scale)",
                "type": "log",
                "autorange": True
            },
            "yaxis": {
                "title": "Text Color (Hex)",
                "tickmode": "array",
                "tickvals": top_colors,
                # "ticktext": [f"{c} ({total_counts[c]})" for c in top_colors]
            },
            "barmode": "stack",
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portals", "x": 1, "y": 1},
            "height": max(300, len(top_colors) * 30)  # Dynamic height
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': sum(total_counts.values()),
        'chart_type': 'text_color_usage_bar'
    }
    return render(request, 'visualizer/chart_page.html', context)

def hashtag_group_usage_radial_bild_view(request):
    """Radial bar chart of hashtag group usage frequency for Bild"""
    # Fetch data for Bild only (owner_id = 8537434)
    portal_id = 8537434  # Bild
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        owner_id=portal_id
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available for Bild"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_bild'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count group occurrences for Bild
    group_counts = Counter()
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        group_counts.update(unique_groups)

    if not group_counts:
        fig = {"data": [], "layout": {"title": "No Hashtag Groups Found for Bild"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_bild'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Prepare data for radial chart
    groups = list(group_counts.keys())
    counts = [group_counts[group] for group in groups]
    theta = [i * (360 / len(groups)) for i in range(len(groups))]  # Evenly spaced angles
    hover_texts = [f"Group: {g}<br>Count: {c}" for g, c in zip(groups, counts)]

    short_groups = [g[:15] + "..." if len(g) > 15 else g for g in groups]

    # Create Plotly radial bar chart
    fig = {
        "data": [{
            "r": counts,
            "theta": theta,
            "type": "barpolar",
            "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # Bild orange
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.8
        }],
        "layout": {
            "title": f"Hashtag Group Usage Frequency for {PORTAL_MAPPING[portal_id]['name']}",
            "polar": {
                "radialaxis": {"title": "Number of Posts"},
                "angularaxis": {
                    "title": "Hashtag Group",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": theta,
                    "ticktext": short_groups
                }
            },
            "template": "seaborn",
            "hovermode": "closest"
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': scrape_data.count(),
        'chart_type': 'hashtag_group_usage_radial_bild'
    }
    return render(request, 'visualizer/chart_page.html', context)

def hashtag_group_usage_radial_zdf_view(request):
    """Radial bar chart of hashtag group usage frequency for ZDF with short labels"""
    # Fetch data for ZDF only (owner_id = 1383406462)
    portal_id = 1383406462  # ZDF
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        owner_id=portal_id
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available for ZDF"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_zdf'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count group occurrences for ZDF
    group_counts = Counter()
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        group_counts.update(unique_groups)

    if not group_counts:
        fig = {"data": [], "layout": {"title": "No Hashtag Groups Found for ZDF"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_zdf'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Prepare data for radial chart
    groups = list(group_counts.keys())
    counts = [group_counts[group] for group in groups]
    theta = [i * (360 / len(groups)) for i in range(len(groups))]  # Evenly spaced angles
    short_groups = [g[:15] + "..." if len(g) > 15 else g for g in groups]  # Shorten labels
    hover_texts = [f"Group: {g}<br>Count: {c}" for g, c in zip(groups, counts)]

    # Create Plotly radial bar chart
    fig = {
        "data": [{
            "r": counts,
            "theta": theta,
            "type": "barpolar",
            "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # ZDF blue
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.8
        }],
        "layout": {
            "title": f"Hashtag Group Usage Frequency for {PORTAL_MAPPING[portal_id]['name']}",
            "polar": {
                "radialaxis": {"title": "Number of Posts"},
                "angularaxis": {
                    "title": "Hashtag Group",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": theta,
                    "ticktext": short_groups  # Use shortened labels
                }
            },
            "template": "seaborn",
            "hovermode": "closest"
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': scrape_data.count(),
        'chart_type': 'hashtag_group_usage_radial_zdf'
    }
    return render(request, 'visualizer/chart_page.html', context)

def hashtag_group_usage_radial_sz_view(request):
    """Radial bar chart of hashtag group usage frequency for SZ with short labels"""
    # Fetch data for SZ only (owner_id = 1647208845)
    portal_id = 1647208845  # SZ
    scrape_data = ScrapeData.objects.filter(
        extracted_hashtags__isnull=False,
        owner_id=portal_id
    )

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available for SZ"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_sz'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Load hashtag group mapping
    with open(MAPPING_FILE_PATH, 'r') as f:
        mapping = json.load(f)["mapping"]

    # Create a hashtag-to-group lookup
    hashtag_to_group = {}
    for group, clusters in mapping.items():
        for cluster, hashtags in clusters.items():
            for hashtag in hashtags:
                hashtag_to_group[hashtag.lower()] = group

    # Count group occurrences for SZ
    group_counts = Counter()
    for entry in scrape_data:
        hashtags = entry.extracted_hashtags if isinstance(entry.extracted_hashtags, list) else json.loads(entry.extracted_hashtags)
        unique_groups = set(hashtag_to_group.get(tag.lower()) for tag in hashtags if tag.lower() in hashtag_to_group)
        group_counts.update(unique_groups)

    if not group_counts:
        fig = {"data": [], "layout": {"title": "No Hashtag Groups Found for SZ"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'hashtag_group_usage_radial_sz'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Prepare data for radial chart
    groups = list(group_counts.keys())
    counts = [group_counts[group] for group in groups]
    theta = [i * (360 / len(groups)) for i in range(len(groups))]  # Evenly spaced angles
    short_groups = [g[:15] + "..." if len(g) > 15 else g for g in groups]  # Shorten labels
    hover_texts = [f"Group: {g}<br>Count: {c}" for g, c in zip(groups, counts)]

    # Create Plotly radial bar chart
    fig = {
        "data": [{
            "r": counts,
            "theta": theta,
            "type": "barpolar",
            "marker": {"color": PORTAL_MAPPING[portal_id]["color"]},  # SZ green
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.8
        }],
        "layout": {
            "title": f"Hashtag Group Usage Frequency for {PORTAL_MAPPING[portal_id]['name']}",
            "polar": {
                "radialaxis": {"title": "Number of Posts"},
                "angularaxis": {
                    "title": "Hashtag Group",
                    "direction": "clockwise",
                    "tickmode": "array",
                    "tickvals": theta,
                    "ticktext": short_groups  # Use shortened labels
                }
            },
            "template": "seaborn",
            "hovermode": "closest"
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': scrape_data.count(),
        'chart_type': 'hashtag_group_usage_radial_sz'
    }
    return render(request, 'visualizer/chart_page.html', context)

def rgb_to_luminance(rgb_array):
    # Normalize RGB to 0-1 range
    rgb_normalized = rgb_array / 255.0
    # Weights based on human perception of brightness
    weights = np.array([0.299, 0.587, 0.114])
    # Calculate luminance
    return np.sum(rgb_normalized * weights)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])

def text_vs_background_luminance_view(request):
    """Scatter plot of text color luminance vs. background color luminance"""
    # Fetch data
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        text_colors__isnull=False,
        bounding_boxes__isnull=False,
        background_color__isnull=False
    )

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_vs_background_luminance'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id
    image_to_owner = {entry.img_name: entry.owner_id for entry in scrape_data}

    # Collect luminance data per portal
    data_by_portal = {pid: {'text_lum': [], 'bg_lum': [], 'colors': []} for pid in VALID_PORTAL_IDS}
    for entry in analyzer_data:
        if entry.image_name in image_to_owner:
            portal_id = image_to_owner[entry.image_name]
            colors = json.loads(entry.text_colors) if isinstance(entry.text_colors, str) else entry.text_colors
            boxes = json.loads(entry.bounding_boxes) if isinstance(entry.bounding_boxes, str) else entry.bounding_boxes
            if len(colors) != len(boxes):
                continue  # Skip if mismatch
            bg_color = entry.background_color
            bg_rgb = hex_to_rgb(bg_color)
            bg_lum = rgb_to_luminance(bg_rgb)

            for color in colors:
                text_rgb = hex_to_rgb(color.lower())
                text_lum = rgb_to_luminance(text_rgb)
                data_by_portal[portal_id]['text_lum'].append(text_lum)
                data_by_portal[portal_id]['bg_lum'].append(bg_lum)
                data_by_portal[portal_id]['colors'].append(color.lower())

    # Check if there's data
    total_points = sum(len(d['text_lum']) for d in data_by_portal.values())
    if total_points == 0:
        fig = {"data": [], "layout": {"title": "No Valid Color Data Found"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_vs_background_luminance'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Prepare traces for each portal
    traces = []
    for portal_id in VALID_PORTAL_IDS:
        text_lum = data_by_portal[portal_id]['text_lum']
        bg_lum = data_by_portal[portal_id]['bg_lum']
        if not text_lum:
            continue

        # Hover texts
        hover_texts = [f"Text Color: {c}<br>Text Lum: {t:.2f}<br>BG Lum: {b:.2f}<br>Portal: {PORTAL_MAPPING[portal_id]['name']}" 
                       for c, t, b in zip(data_by_portal[portal_id]['colors'], text_lum, bg_lum)]

        traces.append({
            "x": text_lum,
            "y": bg_lum,
            "type": "scatter",
            "mode": "markers",
            "name": PORTAL_MAPPING[portal_id]["name"],
            "marker": {
                # "color": [entry['color'] for entry in data_by_portal],  # Use portal colors
                "color": data_by_portal[portal_id]["colors"],  # Use portal color for dots
                "size": 2.5,  # Uniform size
                # "line": {"width": 0.1, "color": "#000000"}  # Black outline
            },
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.7
        })

    # Create colored ticks for the axes
    tick_values = [i * 0.1 for i in range(11)]  # Ticks at 0.0, 0.1, ..., 1.0
    tick_colors = [f"hsl(0, 0%, {int(lum * 100)}%)" for lum in tick_values]  # Grayscale colors for ticks

    # Create Plotly scatter chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Text Color Luminance vs. Background Color Luminance",
            "xaxis": {
                "title": "Text Color Luminance (0-1)",
                "range": [0, 1],
                "tickvals": tick_values,
                "ticktext": [f"{lum:.1f}" for lum in tick_values],
                "tickcolor": tick_colors,  # Color ticks
                "ticklen": 10,  # Length of ticks
                "tickwidth": 2  # Width of ticks
            },
            "yaxis": {
                "title": "Background Color Luminance (0-1)",
                "range": [0, 1],
                "tickvals": tick_values,
                "ticktext": [f"{lum:.1f}" for lum in tick_values],
                "tickcolor": tick_colors,  # Color ticks
                "ticklen": 10,  # Length of ticks
                "tickwidth": 2  # Width of ticks
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portals", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': total_points,
        'chart_type': 'text_vs_background_luminance'
    }
    return render(request, 'visualizer/chart_page.html', context)


def text_vs_background_color_view(request):
    """Scatter plot of text color luminance vs. background color gradient"""
    # Fetch data
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        text_colors__isnull=False,
        bounding_boxes__isnull=False,
        background_color__isnull=False
    )

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_vs_background_color'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id
    image_to_owner = {entry.img_name: entry.owner_id for entry in scrape_data}

    # Collect data per portal
    data_by_portal = {pid: {'text_lum': [], 'bg_rgb': [], 'colors': []} for pid in VALID_PORTAL_IDS}
    for entry in analyzer_data:
        if entry.image_name in image_to_owner:
            portal_id = image_to_owner[entry.image_name]
            colors = json.loads(entry.text_colors) if isinstance(entry.text_colors, str) else entry.text_colors
            boxes = json.loads(entry.bounding_boxes) if isinstance(entry.bounding_boxes, str) else entry.bounding_boxes
            if len(colors) != len(boxes):
                continue
            bg_rgb = hex_to_rgb(entry.background_color)
            bg_y = int(np.mean(bg_rgb))  # Convert to int after mean

            for color in colors:
                text_rgb = hex_to_rgb(color.lower())
                text_lum = rgb_to_luminance(np.array(text_rgb))  # Convert to np.array only here
                data_by_portal[portal_id]['text_lum'].append(text_lum)
                data_by_portal[portal_id]['bg_rgb'].append(bg_y)
                data_by_portal[portal_id]['colors'].append(color.lower())

    total_points = sum(len(d['text_lum']) for d in data_by_portal.values())
    if total_points == 0:
        fig = {"data": [], "layout": {"title": "No Valid Color Data Found"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'text_vs_background_color'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Create gradient background (white to black via rainbow)
    y_vals = np.linspace(0, 255, 256).tolist()  # Convert to list
    x_vals = [0, 1]  # Already a list
    z = [[y for y in y_vals] for _ in range(2)]  # Create 2D list manually
    colorscale = [
        [0.0, '#ffffff'],  # White
        [0.2, '#ff0000'],  # Red
        [0.4, '#ffff00'],  # Yellow
        [0.6, '#00ff00'],  # Green
        [0.8, '#0000ff'],  # Blue
        [1.0, '#000000']   # Black
    ]

    # Prepare traces
    traces = [
        {
            "z": z,
            "x": x_vals,
            "y": y_vals,
            "type": "heatmap",
            "colorscale": colorscale,
            "showscale": False,
            "opacity": 0.5
        }
    ]

    # Add scatter points for each portal
    for portal_id in VALID_PORTAL_IDS:
        text_lum = data_by_portal[portal_id]['text_lum']
        bg_y = data_by_portal[portal_id]['bg_rgb']
        colors = data_by_portal[portal_id]['colors']
        if not text_lum:
            continue

        point_counts = Counter(zip(text_lum, bg_y))
        sizes = [5 + 10 * point_counts[(t, b)] for t, b in zip(text_lum, bg_y)]
        hover_texts = [f"Text Color: {c}<br>Text Lum: {t:.2f}<br>BG Color (mean RGB): {b}<br>Portal: {PORTAL_MAPPING[portal_id]['name']}" 
                       for c, t, b in zip(colors, text_lum, bg_y)]

        traces.append({
            "x": text_lum,
            "y": bg_y,
            "type": "scatter",
            "mode": "markers",
            "name": PORTAL_MAPPING[portal_id]["name"],
            "marker": {
                "color": colors,
                "size": sizes,
                "line": {"width": 1, "color": PORTAL_MAPPING[portal_id]["color"]}
            },
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "opacity": 0.7
        })

    # Create Plotly chart
    fig = {
        "data": traces,
        "layout": {
            "title": "Text Color Luminance vs. Background Color Gradient",
            "xaxis": {
                "title": "Text Color Luminance (0-1)",
                "range": [0, 1]
            },
            "yaxis": {
                "title": "Background Color (Gradient)",
                "range": [0, 255],
                "tickvals": [0, 64, 128, 192, 255],
                "ticktext": ["White", "Light", "Medium", "Dark", "Black"]
            },
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Portals", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': total_points,
        'chart_type': 'text_vs_background_color'
    }
    return render(request, 'visualizer/chart_page.html', context)
class FromUnixTimestamp(Func):
    function = "DATETIME"
    template = "%(function)s(%(expressions)s, 'unixepoch')"

def font_size_per_portal_view(request):
    """Visualize average font sizes per portal"""
    # Fetch data, linking ScrapeData and AnalyzerResult
    scrape_data = ScrapeData.objects.filter(
        img_name__isnull=False,
        owner_id__in=VALID_PORTAL_IDS
    )
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        font_sizes__isnull=False
    )

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'font_size_per_portal'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Link image_name to owner_id and compute average font size per image
    owner_id_map = {entry.img_name: entry.owner_id for entry in scrape_data}
    font_sizes_by_portal = {pid: [] for pid in VALID_PORTAL_IDS}

    for entry in analyzer_data:
        if entry.image_name in owner_id_map:
            owner_id = owner_id_map[entry.image_name]
            # Parse font_sizes (could be list or JSON string)
            font_sizes = entry.font_sizes if isinstance(entry.font_sizes, list) else json.loads(entry.font_sizes)
            if font_sizes:  # Ensure it’s not empty
                avg_font_size = statistics.mean(font_sizes)  # Average per image
                font_sizes_by_portal[owner_id].append(avg_font_size)

    # Prepare data for Plotly box plot
    traces = []
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # ZDF, Bild, SZ

    for i, portal_id in enumerate(VALID_PORTAL_IDS):
        sizes = font_sizes_by_portal[portal_id]
        if sizes:  # Only include portals with data
            portal_name = PORTAL_MAPPING[portal_id]
            traces.append({
                "y": sizes,
                "type": "box",
                "name": portal_name,
                "marker": {"color": colors[i]},
                "boxpoints": "outliers",  # Show outliers
                "jitter": 0.3,  # Spread points for visibility
                "pointpos": -1.8  # Position points to the left
            })

    # Create Plotly box plot
    fig = {
        "data": traces,
        "layout": {
            "title": "Font Size Distribution Per Portal",
            "xaxis": {"title": "Portal"},
            "yaxis": {"title": "Average Font Size (pixels)"},
            "template": "seaborn",
            "hovermode": "closest",
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': sum(len(sizes) for sizes in font_sizes_by_portal.values()),
        'chart_type': 'font_size_per_portal'
    }
    return render(request, 'visualizer/chart_page.html', context)

def background_color_over_time_view(request):
    """Visualize background colors over time"""
    # Fetch data from both models
    scrape_data = ScrapeData.objects.filter(img_name__isnull=False).order_by('taken_at_timestamp')
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False, background_color__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'background_color_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Create a dictionary to map image_name to background_color
    color_dict = {entry.image_name: entry.background_color for entry in analyzer_data}

    # Collect individual data points
    dates = []
    colors = []
    y_positions = []  # Small y-values to spread points slightly

    for i, entry in enumerate(scrape_data):
        if entry.img_name in color_dict:
            dt = datetime.fromtimestamp(entry.taken_at_timestamp)
            date_str = dt.strftime('%Y-%m-%d')
            color = color_dict[entry.img_name]
            dates.append(date_str)
            colors.append(color)
            y_positions.append(i % 10 * 0.1)  # Spread points vertically (0 to 0.9)

    # Prepare hover texts
    hover_texts = [f"Date: {d}<br>Background Color: {c}" for d, c in zip(dates, colors)]

    # Create Plotly scatter plot
    fig = {
        "data": [{
            "x": dates,
            "y": y_positions,
            "type": "scatter",
            "mode": "markers",
            "marker": {
                "size": 12,
                "color": colors,  # Use hex codes directly to color markers
                "line": {"width": 1, "color": "#000000"}  # Black outline for visibility
            },
            "text": hover_texts,
            "hovertemplate": "%{text}",
            "name": "Background Colors"
        }],
        "layout": {
            "title": "Background Colors Over Time",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Index (Spread)", "range": [0, 1], "showticklabels": False},  # Hide y-axis labels
            "template": "seaborn",
            "hovermode": "closest",
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(dates),
        'chart_type': 'background_color_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

def sentiment_over_time_view(request):
    """Visualize sentiment scores (VADER and DeepSeek) over time without averaging"""
    # Fetch data from both models
    scrape_data = ScrapeData.objects.filter(img_name__isnull=False).order_by('taken_at_timestamp')
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

    if not scrape_data.exists() or not analyzer_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'sentiment_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Create a dictionary to map image_name to sentiment scores
    sentiment_dict = {}
    for entry in analyzer_data:
        vader_score = None
        deepseek_score = None
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, dict):
                vader_score = entry.sentiment_vader.get("score")
            elif isinstance(entry.sentiment_vader, str):
                try:
                    vader_data = json.loads(entry.sentiment_vader)
                    vader_score = vader_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if entry.sentiment_deepseek:
            if isinstance(entry.sentiment_deepseek, dict):
                deepseek_score = entry.sentiment_deepseek.get("score")
            elif isinstance(entry.sentiment_deepseek, str):
                try:
                    deepseek_data = json.loads(entry.sentiment_deepseek)
                    deepseek_score = deepseek_data.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
        if vader_score is not None or deepseek_score is not None:
            sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}

    # Collect all individual data points
    vader_dates = []
    vader_scores = []
    deepseek_dates = []
    deepseek_scores = []

    for entry in scrape_data:
        if entry.img_name in sentiment_dict:
            dt = datetime.fromtimestamp(entry.taken_at_timestamp)
            date_str = dt.strftime('%Y-%m-%d')
            sentiments = sentiment_dict[entry.img_name]
            
            if sentiments["vader"] is not None:
                vader_dates.append(date_str)
                vader_scores.append(sentiments["vader"])
            if sentiments["deepseek"] is not None:
                deepseek_dates.append(date_str)
                deepseek_scores.append(sentiments["deepseek"])

    # Prepare hover texts
    vader_hover = [f"Date: {d}<br>VADER Sentiment: {s:.2f}" for d, s in zip(vader_dates, vader_scores)]
    deepseek_hover = [f"Date: {d}<br>DeepSeek Sentiment: {s:.2f}" for d, s in zip(deepseek_dates, deepseek_scores)]

    # Create Plotly chart with two traces
    fig = {
        "data": [
            {
                "x": vader_dates,
                "y": vader_scores,
                "type": "scatter",
                "mode": "markers",  # Changed to markers only for clarity with many points
                "name": "VADER Sentiment",
                "marker": {"size": 8, "color": "#ff7f0e"},
                "text": vader_hover,
                "hovertemplate": "%{text}",
            },
            {
                "x": deepseek_dates,
                "y": deepseek_scores,
                "type": "scatter",
                "mode": "markers",  # Changed to markers only
                "name": "DeepSeek Sentiment",
                "marker": {"size": 8, "color": "#1f77b4"},
                "text": deepseek_hover,
                "hovertemplate": "%{text}",
            }
        ],
        "layout": {
            "title": "Sentiment Over Time (Individual Points)",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Sentiment Score", "range": [-1, 1]},
            "template": "seaborn",
            "hovermode": "closest",
            "legend": {"title": "Sentiment Type", "x": 1, "y": 1}
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(vader_dates) + len(deepseek_dates),
        'chart_type': 'sentiment_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

# def sentiment_over_time_view(request):
#     """Visualize sentiment scores (VADER and DeepSeek) over time"""
#     # Fetch data from both models
#     scrape_data = ScrapeData.objects.filter(img_name__isnull=False).order_by('taken_at_timestamp')
#     analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)

#     # Debugging: Check if data exists
#     print(f"ScrapeData count: {scrape_data.count()}")
#     print(f"AnalyzerResult count: {analyzer_data.count()}")

#     if not scrape_data.exists() or not analyzer_data.exists():
#         fig = {"data": [], "layout": {"title": "No Data Available"}}
#         context = {
#             'plot_json': json.dumps(fig),
#             'data_count': 0,
#             'chart_type': 'sentiment_over_time'
#         }
#         return render(request, 'visualizer/chart_page.html', context)

#     # Create a dictionary to map image_name to sentiment scores
#     sentiment_dict = {}
#     for entry in analyzer_data:
#         vader_score = None
#         deepseek_score = None
#         # Handle JSON parsing for sentiment_vader
#         if entry.sentiment_vader:
#             if isinstance(entry.sentiment_vader, dict):
#                 vader_score = entry.sentiment_vader.get("score")
#             elif isinstance(entry.sentiment_vader, str):
#                 try:
#                     vader_data = json.loads(entry.sentiment_vader)
#                     vader_score = vader_data.get("score")
#                 except (json.JSONDecodeError, TypeError):
#                     print(f"Invalid VADER JSON for {entry.image_name}: {entry.sentiment_vader}")
#         # Handle JSON parsing for sentiment_deepseek
#         if entry.sentiment_deepseek:
#             if isinstance(entry.sentiment_deepseek, dict):
#                 deepseek_score = entry.sentiment_deepseek.get("score")
#             elif isinstance(entry.sentiment_deepseek, str):
#                 try:
#                     deepseek_data = json.loads(entry.sentiment_deepseek)
#                     deepseek_score = deepseek_data.get("score")
#                 except (json.JSONDecodeError, TypeError):
#                     print(f"Invalid DeepSeek JSON for {entry.image_name}: {entry.sentiment_deepseek}")
#         if vader_score is not None or deepseek_score is not None:
#             sentiment_dict[entry.image_name] = {"vader": vader_score, "deepseek": deepseek_score}
#             print(f"Linked {entry.image_name}: VADER={vader_score}, DeepSeek={deepseek_score}")

#     # Debugging: Check if sentiment_dict has data
#     print(f"Sentiment mappings found: {len(sentiment_dict)}")

#     # Aggregate sentiment by date
#     vader_by_date = defaultdict(float)
#     deepseek_by_date = defaultdict(float)
#     vader_count = defaultdict(int)
#     deepseek_count = defaultdict(int)

#     for entry in scrape_data:
#         if entry.img_name in sentiment_dict:
#             dt = datetime.fromtimestamp(entry.taken_at_timestamp)
#             date_key = dt.date()
#             sentiments = sentiment_dict[entry.img_name]
            
#             if sentiments["vader"] is not None:
#                 vader_by_date[date_key] += sentiments["vader"]
#                 vader_count[date_key] += 1
#             if sentiments["deepseek"] is not None:
#                 deepseek_by_date[date_key] += sentiments["deepseek"]
#                 deepseek_count[date_key] += 1

#     # Calculate average sentiment per day
#     dates = sorted(set(vader_by_date.keys()) | set(deepseek_by_date.keys()))
#     date_strings = [d.strftime('%Y-%m-%d') for d in dates]
#     vader_scores = [vader_by_date[d] / vader_count[d] if vader_count[d] > 0 else None for d in dates]
#     deepseek_scores = [deepseek_by_date[d] / deepseek_count[d] if deepseek_count[d] > 0 else None for d in dates]

#     # Debugging: Check aggregated data
#     print(f"Dates: {date_strings}")
#     print(f"VADER Scores: {vader_scores}")
#     print(f"DeepSeek Scores: {deepseek_scores}")

#     # Prepare hover texts
#     vader_hover = [f"Date: {d}<br>VADER Sentiment: {s:.2f}" if s is not None else f"Date: {d}<br>No VADER Data" 
#                    for d, s in zip(date_strings, vader_scores)]
#     deepseek_hover = [f"Date: {d}<br>DeepSeek Sentiment: {s:.2f}" if s is not None else f"Date: {d}<br>No DeepSeek Data" 
#                       for d, s in zip(date_strings, deepseek_scores)]

#     # Create Plotly chart with two traces
#     fig = {
#         "data": [
#             {
#                 "x": date_strings,
#                 "y": vader_scores,
#                 "type": "scatter",
#                 "mode": "lines+markers",
#                 "name": "VADER Sentiment",
#                 "line": {"color": "#ff7f0e"},
#                 "marker": {"size": 8},
#                 "text": vader_hover,
#                 "hovertemplate": "%{text}",
#             },
#             {
#                 "x": date_strings,
#                 "y": deepseek_scores,
#                 "type": "scatter",
#                 "mode": "lines+markers",
#                 "name": "DeepSeek Sentiment",
#                 "line": {"color": "#1f77b4"},
#                 "marker": {"size": 8},
#                 "text": deepseek_hover,
#                 "hovertemplate": "%{text}",
#             }
#         ],
#         "layout": {
#             "title": "Sentiment Over Time",
#             "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
#             "yaxis": {"title": "Sentiment Score", "range": [-1, 1]},
#             "template": "seaborn",
#             "hovermode": "closest",
#             "legend": {"title": "Sentiment Type", "x": 1, "y": 1}
#         }
#     }

#     context = {
#         'plot_json': json.dumps(fig),
#         'data_count': len(dates),
#         'chart_type': 'sentiment_over_time'
#     }
#     return render(request, 'visualizer/chart_page.html', context)

def likes_over_time_view(request):
    """Visualize total likes over time based on taken_at_timestamp"""
    # Fetch all ScrapeData entries, ordered by timestamp
    scrape_data = ScrapeData.objects.filter(taken_at_timestamp__isnull=False).order_by('taken_at_timestamp')

    if not scrape_data.exists():
        fig = {"data": [], "layout": {"title": "No Data Available"}}
        context = {
            'plot_json': json.dumps(fig),
            'data_count': 0,
            'chart_type': 'likes_over_time'
        }
        return render(request, 'visualizer/chart_page.html', context)

    # Aggregate likes by day in Python
    likes_by_date = defaultdict(int)
    for entry in scrape_data:
        # Convert Unix timestamp to datetime
        dt = datetime.fromtimestamp(entry.taken_at_timestamp)
        # Truncate to date (remove time)
        date_key = dt.date()
        likes_by_date[date_key] += entry.likes_count

    # Prepare data for Plotly
    dates = sorted(likes_by_date.keys())
    # Convert dates to strings for JSON serialization
    date_strings = [d.strftime('%Y-%m-%d') for d in dates]
    total_likes = [likes_by_date[date] for date in dates]
    hover_texts = [f"Date: {d}<br>Total Likes: {l}" for d, l in zip(date_strings, total_likes)]

    # Create Plotly line chart
    fig = {
        "data": [{
            "x": date_strings,  # Use string dates here
            "y": total_likes,
            "type": "scatter",
            "mode": "lines+markers",
            "line": {"color": "#00cc96"},
            "marker": {"size": 8},
            "text": hover_texts,
            "hovertemplate": "%{text}",
        }],
        "layout": {
            "title": "Likes Over Time",
            "xaxis": {"title": "Date", "tickformat": "%Y-%m-%d"},
            "yaxis": {"title": "Total Likes"},
            "template": "seaborn",
            "hovermode": "closest"
        }
    }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(dates),
        'chart_type': 'likes_over_time'
    }
    return render(request, 'visualizer/chart_page.html', context)

def text_color_vs_background_color_view(request):
    """Visualize most dominant text color vs background color"""
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        background_color__isnull=False,
        text_colors__isnull=False
    )[:300]

    # Aggregate data by background color and determine dominant text color
    color_data = defaultdict(lambda: defaultdict(int))
    for entry in analyzer_data:
        if not entry.background_color or not entry.text_colors:
            continue
            
        # Parse text_colors (assuming it's a JSON string like "[\"#767c83\", \"#000000\", ...]")
        try:
            text_colors = json.loads(entry.text_colors) if isinstance(entry.text_colors, str) else entry.text_colors
            if not isinstance(text_colors, list) or not text_colors:
                continue
        except (json.JSONDecodeError, TypeError):
            continue

        # Count frequency of each text color for this background color
        for color in text_colors:
            color_data[entry.background_color][color] += 1

    # Determine the most dominant text color for each background color
    aggregated_data = {}
    for bg_color, text_color_counts in color_data.items():
        if text_color_counts:
            # Find the text color with the highest count
            dominant_text_color = max(text_color_counts.items(), key=lambda x: x[1])[0]
            aggregated_data[bg_color] = {
                'dominant_text_color': dominant_text_color,
                'count': sum(text_color_counts.values())  # Total samples for hover info
            }

    # Prepare Plotly bar chart
    if aggregated_data:
        bg_colors = list(aggregated_data.keys())
        text_colors = [data['dominant_text_color'] for data in aggregated_data.values()]
        hover_texts = [
            f"Background: {bg_color}<br>Dominant Text: {data['dominant_text_color']}<br>Samples: {data['count']}"
            for bg_color, data in aggregated_data.items()
        ]

        fig = {
            "data": [{
                "x": bg_colors,
                "y": [1] * len(bg_colors),  # Uniform height for visualization
                "type": "bar",
                "marker": {
                    "color": text_colors,  # Use text colors for bar colors
                    "line": {"color": bg_colors, "width": 2}  # Outline with background color
                },
                "text": hover_texts,
                "hovertemplate": "%{text}",
                "showlegend": False
            }],
            "layout": {
                "title": "Dominant Text Color by Background Color",
                "xaxis": {"title": "Background Color", "tickangle": -45},
                "yaxis": {"title": "Presence", "showticklabels": False},  # Hide y-axis labels since height is uniform
                "template": "seaborn",
                "bargap": 0.2
            }
        }
    else:
        fig = {"data": [], "layout": {"title": "No Data Available"}}

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(analyzer_data),
        'chart_type': 'text_color_vs_background_color'
    }
    return render(request, 'visualizer/chart_page.html', context)

def background_color_vs_sentiment_view(request):
    """Visualize background color vs sentiment (VADER and DeepSeek)"""
    analyzer_data = AnalyzerResult.objects.filter(
        image_name__isnull=False,
        background_color__isnull=False
    )[:300]

    # Aggregate data by background color
    color_sentiments = defaultdict(lambda: {'vader': [], 'deepseek': []})
    for entry in analyzer_data:
        if not entry.background_color:
            continue
            
        # Process VADER sentiment
        if entry.sentiment_vader:
            try:
                vader_data = json.loads(entry.sentiment_vader) if isinstance(entry.sentiment_vader, str) else entry.sentiment_vader
                if isinstance(vader_data, dict) and "score" in vader_data:
                    color_sentiments[entry.background_color]['vader'].append(vader_data["score"])
            except (json.JSONDecodeError, TypeError):
                continue

        # Process DeepSeek sentiment
        if entry.sentiment_deepseek:
            try:
                deepseek_data = json.loads(entry.sentiment_deepseek) if isinstance(entry.sentiment_deepseek, str) else entry.sentiment_deepseek
                if isinstance(deepseek_data, dict) and "score" in deepseek_data:
                    color_sentiments[entry.background_color]['deepseek'].append(deepseek_data["score"])
            except (json.JSONDecodeError, TypeError):
                continue

    # Calculate average sentiments per color
    aggregated_data = {
        color: {
            'vader_avg': sum(data['vader']) / len(data['vader']) if data['vader'] else 0,
            'deepseek_avg': sum(data['deepseek']) / len(data['deepseek']) if data['deepseek'] else 0,
            'count': len(data['vader']) + len(data['deepseek'])  # Total samples for hover info
        }
        for color, data in color_sentiments.items()
    }

    # Prepare Plotly bar chart with grouped bars
    if aggregated_data:
        colors = list(aggregated_data.keys())
        vader_avg = [data['vader_avg'] for data in aggregated_data.values()]
        deepseek_avg = [data['deepseek_avg'] for data in aggregated_data.values()]
        hover_texts = [
            f"Color: {color}<br>VADER Avg: {data['vader_avg']:.2f}<br>DeepSeek Avg: {data['deepseek_avg']:.2f}<br>Samples: {data['count']}"
            for color, data in aggregated_data.items()
        ]

        fig = {
            "data": [
            {
                "x": colors,
                "y": vader_avg,
                "type": "bar",
                "name": "VADER Sentiment",
                "marker": {"color": "#722222"},
                "text": hover_texts,
                "hovertemplate": "%{text}",
            },
            {
                "x": colors,
                "y": deepseek_avg,
                "type": "bar",
                "name": "DeepSeek Sentiment",
                "marker": {"color": "#0000FF"},  # Changed to blue color
                "text": hover_texts,
                "hovertemplate": "%{text}",
            }
            ],
            "layout": {
            "title": "Average Sentiment by Background Color",
            "xaxis": {"title": "Background Color", "tickangle": -45},
            "yaxis": {"title": "Average Sentiment Score"},
            "barmode": "group",  # Group bars side by side
            "template": "seaborn",
            "legend": {"x": 1, "y": 1}
            }
        }
    else:
        fig = {"data": [], "layout": {"title": "No Data Available"}}

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(analyzer_data),
        'chart_type': 'background_color_vs_sentiment'
    }
    return render(request, 'visualizer/chart_page.html', context)

def likes_vs_sentiment_view(request):
    """Visualize likes_count vs sentiment_vader polarity"""
    scrape_data = ScrapeData.objects.filter(img_name__isnull=False)[:300]
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)[:300]

    # Map image_name to sentiment_vader score
    sentiment_dict = {}
    for entry in analyzer_data:
        if entry.sentiment_vader:
            if isinstance(entry.sentiment_vader, str):
                try:
                    sentiment_data = json.loads(entry.sentiment_vader)
                except json.JSONDecodeError:
                    continue
            else:
                sentiment_data = entry.sentiment_vader
            if isinstance(sentiment_data, dict) and "score" in sentiment_data:
                sentiment_dict[entry.image_name] = sentiment_data["score"]

    # Prepare chart data
    likes = []
    sentiments = []
    hover_texts = []
    for scrape in scrape_data:
        if scrape.img_name in sentiment_dict:
            likes.append(scrape.likes_count)
            sentiments.append(sentiment_dict[scrape.img_name])
            hover_texts.append(f"Image: {scrape.img_name}<br>Likes: {scrape.likes_count}<br>Sentiment: {sentiments[-1]:.2f}")

    # Create Plotly scatter plot
    if likes and sentiments:
        fig = {
            "data": [{
                "x": sentiments,
                "y": likes,
                "type": "scatter",
                "mode": "markers",
                "marker": {"size": 10, "color": sentiments, "colorscale": "Viridis", "showscale": True},
                "text": hover_texts,
                "hovertemplate": "%{text}<br>(Sentiment: %{x:.2f}, Likes: %{y})",
            }],
            "layout": {
                "title": "Likes vs Sentiment Polarity",
                "xaxis": {"title": "Sentiment Polarity (VADER)"},
                "yaxis": {"title": "Likes Count"},
                "template": "seaborn",
                "hovermode": "closest"
            }
        }
    else:
        fig = {"data": [], "layout": {"title": "No Data Available"}}

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(likes),
        'chart_type': 'likes_vs_sentiment'
    }
    return render(request, 'visualizer/chart_page.html', context)

def analyze_view(request):
    """Visualize likes_count vs sentiment_vader polarity"""
    # Fetch data from both models, limiting to 300 entries for performance
    scrape_data = ScrapeData.objects.filter(img_name__isnull=False)[:300]
    analyzer_data = AnalyzerResult.objects.filter(image_name__isnull=False)[:300]

    # Create a dictionary to map image_name to sentiment_vader score
    sentiment_dict = {}
    for entry in analyzer_data:
        if entry.sentiment_vader:
            # If sentiment_vader is a string, parse it; otherwise, assume it's already a dict
            if isinstance(entry.sentiment_vader, str):
                try:
                    sentiment_data = json.loads(entry.sentiment_vader)
                except json.JSONDecodeError:
                    continue  # Skip if JSON is invalid
            else:
                sentiment_data = entry.sentiment_vader
            
            # Check if "score" exists in the parsed data
            if isinstance(sentiment_data, dict) and "score" in sentiment_data:
                sentiment_dict[entry.image_name] = sentiment_data["score"]

    # Prepare data for the chart
    likes = []
    sentiments = []
    hover_texts = []

    for scrape in scrape_data:
        if scrape.img_name in sentiment_dict:
            likes.append(scrape.likes_count)
            sentiments.append(sentiment_dict[scrape.img_name])
            hover_texts.append(f"Image: {scrape.img_name}<br>Likes: {scrape.likes_count}<br>Sentiment: {sentiment_dict[scrape.img_name]:.2f}")

    # Create Plotly scatter plot
    if likes and sentiments:
        fig = {
            "data": [{
                "x": sentiments,
                "y": likes,
                "type": "scatter",
                "mode": "markers",
                "marker": {"size": 10, "color": sentiments, "colorscale": "Viridis", "showscale": True},
                "text": hover_texts,
                "hovertemplate": "%{text}<br>(Sentiment: %{x:.2f}, Likes: %{y})",
            }],
            "layout": {
                "title": "Likes vs Sentiment Polarity",
                "xaxis": {"title": "Sentiment Polarity (VADER)"},
                "yaxis": {"title": "Likes Count"},
                "template": "seaborn",
                "hovermode": "closest"
            }
        }
    else:
        fig = {
            "data": [],
            "layout": {"title": "No Data Available"}
        }

    context = {
        'plot_json': json.dumps(fig),
        'data_count': len(likes),
    }

    return render(request, 'visualizer/chart_page.html', context)

# def analyze_view(request):
#     """Visualize mapped hashtag groups with like counts"""
#     x_field = request.GET.get('x_field', 'hashtag_groups')
#     y_field = request.GET.get('y_field', 'scrape.likes_count')

#     # Fetch posts
#     scrape_data = ScrapeData.objects.all()[:300]

#     # Dictionary to store aggregated like counts per hashtag category
#     category_likes = defaultdict(list)

#     for scrape in scrape_data:
#         hashtags = extract_hashtags(scrape.text)  # Extract hashtags from text
#         matched_categories = set()

#         for hashtag in hashtags:
#             hashtag_lower = hashtag.lstrip("#").lower()  # Normalize hashtag
#             if hashtag_lower in reversed_mapping:
#                 categories = reversed_mapping[hashtag_lower]
#                 for category, _ in categories.items():
#                     matched_categories.add(category)

#         for category in matched_categories:
#             category_likes[category].append(scrape.likes_count)

#     # Aggregate data: Calculate average likes per category
#     aggregated_data = {
#         category: sum(likes) / len(likes) if likes else 0
#         for category, likes in category_likes.items()
#     }

#     # Prepare Plotly chart data
#     if aggregated_data:
#         fig = {
#             "data": [{
#                 "x": list(aggregated_data.keys()),
#                 "y": list(aggregated_data.values()),
#                 "type": "bar",
#                 "hovertemplate": "Category: %{x}<br>Avg Likes: %{y}",
#             }],
#             "layout": {
#                 "title": "Average Likes by Hashtag Category",
#                 "xaxis": {"title": "Hashtag Category"},
#                 "yaxis": {"title": "Average Likes"},
#                 "template": "seaborn"
#             }
#         }
#     else:
#         fig = {"data": [], "layout": {}}

#     context = {
#         'plot_json': json.dumps(fig),
#         'data_count': len(scrape_data),
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