import json
import re
import traceback
from datetime import datetime, date, timedelta
import requests

from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from scraper.models import ScraperRun, ScrapeBatch, ScrapeData


@csrf_exempt
def start(request):
    req_data = []

    if request.method == "GET":
        req_data = request.args

    if request.method == "POST":
        req_data = json.loads(request.body.decode("utf-8"))

    try:
        name = req_data.get("name", "")
        profile_id = req_data.get("profile_id", 0)
        start_cursor = req_data.get("start_cursor", "")  # optional
        scrape_to_date = req_data.get("scrape_to_date", "01.01.2025-0:0:0")  # optional
        scrape_max_notes = req_data.get("scrape_max_notes", 99999)  # optional
        scrape_max_batches = req_data.get("scrape_max_batches", 200)  # optional
        scrape_notes_per_batch = req_data.get("scrape_notes_per_batch", 10)  # optional

        if name == "":
            return JsonResponse({"error": "name is required"}, status=400)

        if profile_id == "":
            return JsonResponse({"error": "profile_id is required"}, status=400)

        scrape_to_date = datetime.strptime(scrape_to_date, "%d.%m.%Y-%H:%M:%S")

        query_id = 17888483320059182

        curr_run = ScraperRun(name=name,
                              profile_id=profile_id,
                              start_cursor=start_cursor,
                              scrape_max_date=scrape_to_date,
                              scrape_max_notes=scrape_max_notes,
                              scrape_max_batches=scrape_max_batches,
                              scrape_notes_per_batch=scrape_notes_per_batch,
                              status="created",
                              total_data_count=0)
        curr_run.save()

        def stream_output():
            try:
                next_cursor = start_cursor

                scraped_bates = 0
                scraped_notes = 0
                date_in_range = True

                dir_ext = re.sub(r'[^a-zA-Z0-9\-]', '', name.lower().replace(" ", "-"))
                img_dir = f"{int(datetime.now().timestamp())}-{dir_ext}"

                # todo mkdir img_dir
                # todo refactor note to node

                def get_graphql_url(cursor=""):
                    after = ""
                    if cursor != "":
                        after = f',"after":"{cursor}"'
                    return f'https://www.instagram.com/graphql/query/?query_id={query_id}&variables={{"id":"{profile_id}","first":{scrape_notes_per_batch}{after}}}'

                def update_run_started(total_data_count):
                    curr_run.status = "running"
                    curr_run.total_data_count = total_data_count
                    curr_run.save()

                def save_img(img_url):
                    # todo add column "img_name" to ScrapeData
                    # todo add column "img_dir" to ScrapeBatch
                    # todo downloade and save img in db and dir

                    return None

                def process_node(node, scrape_batch_id):
                    img_url = node["display_url"]
                    curr_node = ScrapeData(scraper_run_id=curr_run.id,
                                           scrape_batch_id=scrape_batch_id,
                                           node_id=node["id"],
                                           type=node["__typename"],
                                           text=node["edge_media_to_caption"]["edges"][0]["node"]["text"],
                                           shortcode=node["shortcode"],
                                           comment_count=node["edge_media_to_comment"]["count"],
                                           comments_disabled=node["comments_disabled"],
                                           taken_at_timestamp=node["taken_at_timestamp"],
                                           display_height=node["dimensions"]["height"],
                                           display_width=node["dimensions"]["width"],
                                           display_url=img_url,
                                           likes_count=node["edge_media_preview_like"]["count"],
                                           owner_id=node["owner"]["id"],
                                           thumbnail_url=node["thumbnail_url"],
                                           thumbnail_resources=json.dumps(node["thumbnail_resources"]),
                                           is_video=node["is_video"], )

                    curr_node.save()
                    save_img(img_url)

                def process_batch():
                    graphql_url = get_graphql_url(next_cursor)

                    insta_response = requests.get(graphql_url)
                    insta_data = insta_response.json()
                    insta_data_media = insta_data["data"]["user"]["edge_owner_to_timeline_media"]

                    if scraped_bates == 0:
                        update_run_started(insta_data_media["count"])

                    curr_batch = ScrapeBatch(scraper_run_id=curr_run.id,
                                             notes_in_batch=len(insta_data_media["edges"]),
                                             has_next_page=insta_data_media["page_info"]["has_next_page"],
                                             end_cursor=insta_data_media["page_info"]["end_cursor"],
                                             status=insta_data["status"],
                                             extensions=json.dumps(insta_data["extensions"]), )
                    curr_batch.save()

                    for edge in insta_data_media["edges"]:
                        process_node(edge["node"], curr_batch.id)

                    return len(insta_data_media["edges"])

                while scraped_bates < scrape_max_batches and scraped_notes < scrape_max_notes:
                    scraped_notes += process_batch()
                    scraped_bates += 1

                    print(
                        f"scraped_bates:{scraped_bates}, scraped_notes:{scraped_notes}")
                    yield json.dumps({
                        "scraped_bates": scraped_bates,
                        "scraped_notes": scraped_notes
                    }) + "\n"

            except Exception as err:
                yield json.dumps({"error": str(err) + " " + str(traceback.print_exc())}) + "\n"

        response = StreamingHttpResponse(stream_output(), content_type="application/json")
        return response

    except Exception as e:
        return JsonResponse({"error": str(e) + " " + str(traceback.print_exc())}, status=500)
