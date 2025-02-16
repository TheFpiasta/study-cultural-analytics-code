from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_text_sentiment_vader(text):
    """Analyze the sentiment of the text using VADER."""
    try:
        analyzer = SentimentIntensityAnalyzer()
        
        # VADER works well with German, it returns a dictionary with sentiment scores
        sentiment_scores = analyzer.polarity_scores(text)

        # VADER gives polarity as compound, and it's a normalized score from -1 to 1
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
        return 0.0, 0.0  # Return neutral scores in case of error
