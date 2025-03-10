import json
import requests
import re

from django.shortcuts import render
from django.http import JsonResponse
from analyzer.models import AnalyzerResult
from scraper.models import ScrapeData

from django.views.decorators.csrf import csrf_exempt

LM_STUDIO_API = "http://host.docker.internal:1234/v1/chat/completions"  # Docker fix


@csrf_exempt  # Disable CSRF for simplicity (only for testing, be cautious in production)
def chat_with_llm(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "")

            # Constructing the payload
            payload = {
                "model": "deepseek-r1-distill-qwen-7b",
                "messages": [
                    {"role": "system", "content": "You are a concise assistant. Always provide a short, direct answer. Your answer must always start with 'Answer:'."},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 20000  # Allowing enough tokens for reasoning
            }

            # Sending request to LM Studio API
            response = requests.post(LM_STUDIO_API, json=payload)

            response_data = response.json()

            # Extracting the full message
            full_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                # Extract everything after "Answer:"
                match = re.search(r"Answer:\s*(.*)", full_response, re.DOTALL)

                if match:
                    ai_message = match.group(1).strip()  # Extract and clean the answer
                else:
                    ai_message = full_response  # Fallback if "Answer:" isn't found

                return JsonResponse({"response": ai_message})

            except Exception as e:

                return JsonResponse({"error": "Failed to extract answer"}, status=500)

        except Exception as e:

            return JsonResponse({"error": "Internal server error"}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

def chatBot_page(request):
    return render(request, 'chat-bot/chat_page.html')