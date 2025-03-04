from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_text_sentiment_vader(text):
    """Analyze the sentiment of the text using VADER, returning a score and category."""
    try:
        analyzer = SentimentIntensityAnalyzer()
        sentiment_scores = analyzer.polarity_scores(text)

        # Extract compound polarity score
        polarity = sentiment_scores['compound']

        if polarity > 0.5:
            sentiment = "positive"
        elif polarity < -0.5:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return polarity, sentiment
    except Exception as e:
        print(f"Error during sentiment analysis: {e}")
        return 0.0, "neutral"  # Return neutral scores in case of error
