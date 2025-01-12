import json
import traceback
from datetime import datetime, date, timedelta
from time import sleep
import requests

from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def start(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))

            name = data.get("name", "")
            profile_id = data.get("profile_id", 0)
            start_cursor = data.get("start_cursor", "")  # optional
            scrape_to_date = data.get("scrape_to_date", "01.01.2025-0:0:0")  # optional
            scrape_max_notes = data.get("scrape_max_notes", 99999)  # optional
            scrape_max_batches = data.get("scrape_max_batches", 200)  # optional
            scrape_notes_per_batch = data.get("scrape_notes_per_batch", 10)  # optional

            if name == "":
                return JsonResponse({"error": "name is required"}, status=400)

            if profile_id == "":
                return JsonResponse({"error": "profile_id is required"}, status=400)

            scrape_to_date = datetime.strptime(scrape_to_date, "%d.%m.%Y-%H:%M:%S")

            query_id = 17888483320059182

            def stream_output():
                next_cursor = start_cursor

                def get_graphql_url(cursor=""):
                    after = ""
                    if cursor != "":
                        after = f',"after":"{cursor}"'
                    return f'https://www.instagram.com/graphql/query/?query_id={query_id}&variables={{"id":"{profile_id}","first":{scrape_notes_per_batch}{after}}}'

                def process_batch():
                    graphql_url = get_graphql_url(next_cursor)

                    insta_response = requests.get(graphql_url)
                    insta_data = insta_response.json()

                    # todo save insta_data to database
                    # todo downloade image

                    print(insta_data)

                    note_count = 1
                    return {"note_count":note_count, "last_date":datetime.strptime("12.01.2025", "%d.%m.%Y")}

                scraped_bates = 0
                scraped_notes = 0
                date_in_range = True

                try:
                    while scraped_bates < scrape_max_batches and scraped_notes < scrape_max_notes and date_in_range:
                        result = process_batch()
                        scraped_notes += result["note_count"]
                        scraped_bates += 1

                        date_in_range = scrape_to_date <= result["last_date"]

                        print(
                            f"scraped_bates:{scraped_bates}, scraped_notes:{scraped_notes}, date_in_range:{date_in_range}")
                        yield json.dumps({
                            "scraped_bates": scraped_bates,
                            "scraped_notes": scraped_notes,
                            "date_in_range": date_in_range
                        }) + "\n"
                except Exception as err:
                    yield json.dumps({"error": str(err) + " " + str(traceback.print_exc())}) + "\n"

            response = StreamingHttpResponse(stream_output(), content_type="application/json")
            return response

        except Exception as e:
            return JsonResponse({"error": str(e) + " " + str(traceback.print_exc())}, status=500)
