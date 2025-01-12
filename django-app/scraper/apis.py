import json
import traceback
from datetime import datetime, date

from django.http import StreamingHttpResponse, JsonResponse


def start(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            name = data.get("name", "")
            profile_id = data.get("profile_id", 0)
            start_cursor = data.get("start_cursor", "")  # optional
            scrape_max_date = data.get("max_date", date.min)  # optional
            scrape_max_notes = data.get("max_notes", 99999)  # optional
            scrape_max_batches = data.get("max_batches", 200)  # optional
            scrape_notes_per_batch = data.get("notes_per_batch", 10)  # optional

            if name == "":
                return JsonResponse({"error": "name is required"}, status=400)

            if profile_id == "":
                return JsonResponse({"error": "profile_id is required"}, status=400)

            query_id = 17888483320059182

            graphql_url = f'https://www.instagram.com/graphql/query/?query_id={query_id}&variables={{"id":"{profile_id}","first":{scrape_notes_per_batch},"after":{start_cursor}}}'

            scraped_bates = 0
            scraped_notes = 0
            stop_by_date = False



            def stream_output():
                return "Hello World"

            response = StreamingHttpResponse(
                stream_output(), content_type="application/json")
            return response

        except Exception as e:
            return JsonResponse({"error": str(e) + " " + str(traceback.print_exc())}, status=500)
