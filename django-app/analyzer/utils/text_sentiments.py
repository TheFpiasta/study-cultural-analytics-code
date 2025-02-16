from textblob import TextBlob

def analyze_text_sentiment(text):
    """Analyze the sentiment of the text using TextBlob."""
    try:
        # Create a TextBlob object
        blob = TextBlob(text)

        # Get the sentiment polarity and subjectivity
        sentiment = blob.sentiment  # returns a namedtuple with polarity and subjectivity
        
        # Store polarity and subjectivity in the database or return it
        return sentiment.polarity, sentiment.subjectivity
    except Exception as e:
        print(f"Error during sentiment analysis: {e}")
        return None, None
