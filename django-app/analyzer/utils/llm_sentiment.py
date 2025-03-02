import requests
import json
import re

LM_STUDIO_API = "http://host.docker.internal:1234/v1/chat/completions"  # Adjust based on LM Studio settings

def analyze_text_sentiment_llm(text):
    """Analyze the sentiment of the text using a local LLM via LM Studio."""

    try:
        payload = {
            "model": "deepseek-coder-v2-lite-instruct",
            "messages": [
                {"role": "system", "content": (
                    "Du bist ein KI-Assistent für Stimmungsanalyse. "
                    "Lies den folgenden Text und klassifiziere die Stimmung als 'positiv', 'negativ' oder 'neutral'. "
                    "Gib die Antwort **ausschließlich** in diesem exakten Format zurück, ohne jegliche Erklärung oder zusätzliche Zeichen:\n\n"
                    "Stimmung: [Klassifizierung] (Score: [Wert zwischen -1 und 1])\n\n"
                    "Beispiele:\n"
                    "Stimmung: positiv (Score: 0.75)\n"
                    "Stimmung: negativ (Score: -0.6)\n"
                    "Stimmung: neutral (Score: 0.1)\n\n"
                    "Antwort nur im angegebenen Format, keine weiteren Informationen!"
                )},
                {"role": "user", "content": text}
            ],
            "max_tokens": 200  # Reduce to prevent long responses
        }
        response = requests.post(LM_STUDIO_API, json=payload)
        response_data = response.json()

        # full_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # # Extract sentiment and score using regex
        # match = re.search(r"Sentiment:\s*(\w+)\s*\(Score:\s*([\-0-9.]+)\)", full_response)

        # if match:
        #     sentiment = match.group(1).lower()  # Convert to lowercase for consistency
        #     polarity = float(match.group(2))    # Extract score as float
        # else:
        #     sentiment = "neutral"  # Default fallback
        #     polarity = 0.0

        # return polarity, sentiment

        return response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

    except Exception as e:
        print(f"Error during LLM sentiment analysis: {e}")
        return 0.0, "neutral"  # Return neutral values on error
