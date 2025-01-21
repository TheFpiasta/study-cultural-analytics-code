import json
import os
import re
import time
import traceback
import uuid
from datetime import datetime

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
        scrape_max_nodes = req_data.get("scrape_max_nodes", 99999)  # optional
        scrape_max_batches = req_data.get("scrape_max_batches", 200)  # optional
        scrape_nodes_per_batch = req_data.get("scrape_nodes_per_batch", 10)  # optional

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
                              scrape_max_nodes=scrape_max_nodes,
                              scrape_max_batches=scrape_max_batches,
                              scrape_nodes_per_batch=scrape_nodes_per_batch,
                              status="created",
                              total_data_count=0)
        curr_run.save()

        print("create scraper run ...")

        def stream_output():
            try:
                next_cursor = start_cursor

                scraped_bates = 0
                scraped_nodes = 0
                # date_in_range = True

                dir_ext = re.sub(r'[^a-zA-Z0-9\-]', '', name.lower().replace(" ", "-")[0:16])
                img_dir = f"{int(datetime.now().timestamp())}-{dir_ext}"

                img_path = os.path.join(os.getcwd(), 'images', img_dir + "/")
                os.mkdir(img_path)

                if not os.path.exists(img_path):
                    Exception("! [mkdir] img path creation failed for: ", img_path)

                curr_run.img_dir = img_path
                curr_run.save()

                print("start scraper run ...")

                def get_graphql_url(cursor=""):
                    after = ""
                    if cursor != "":
                        after = f',"after":"{cursor}"'
                    return f'https://www.instagram.com/graphql/query/?query_id={query_id}&variables={{"id":"{profile_id}","first":{scrape_nodes_per_batch}{after}}}'

                def update_run_started(total_data_count):
                    curr_run.status = "running"
                    curr_run.total_data_count = total_data_count
                    curr_run.save()

                def download_img(img_url, img_prefix):
                    try:
                        print("downloading img ...")
                        img_response = requests.get(img_url)

                        if img_response.status_code == 200:
                            image_content = img_response.content
                            image_type = \
                                img_response.headers.get("Content-Type", "application/octet-stream").split("/")[-1]
                            image_path = f"{img_path}/{img_prefix}.{image_type}"

                            with open(image_path, "wb") as file:
                                file.write(image_content)

                            print(f"saved img {image_path}")
                            return f"{image_path}"

                        print(f"! [img_download]: {img_prefix} failed with status: {img_response.status_code}")
                        return False

                    except Exception as d_e:
                        print(f"! [img_download]: {img_prefix} failed with Exception: ",
                              str(d_e) + " " + str(traceback.print_exc()))
                        return False

                def process_node(node, scrape_batch):
                    img_url = node["display_url"]
                    img_name = download_img(img_url, f"{time.time_ns()}_{node["shortcode"]}")

                    print(f"saving node {node["id"]}...")

                    curr_node = ScrapeData(scraper_run_id=curr_run,
                                           scrape_batch_id=scrape_batch,
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
                                           thumbnail_src=node["thumbnail_src"],
                                           thumbnail_resources=json.dumps(node["thumbnail_resources"]),
                                           is_video=node["is_video"],
                                           img_name=img_name,
                                           img_download_status="success", )

                    if not img_name:
                        curr_node.img_download_status = "failed"

                    curr_node.save()

                def process_batch():
                    graphql_url = get_graphql_url(next_cursor)

                    insta_response = requests.get(graphql_url)
                    insta_data = insta_response.json()
                    insta_data_media = insta_data["data"]["user"]["edge_owner_to_timeline_media"]

                    if scraped_bates == 0:
                        update_run_started(insta_data_media["count"])

                    curr_batch = ScrapeBatch(scraper_run_id=curr_run,
                                             nodes_in_batch=len(insta_data_media["edges"]),
                                             has_next_page=insta_data_media["page_info"]["has_next_page"],
                                             end_cursor=insta_data_media["page_info"]["end_cursor"],
                                             status=insta_data["status"],
                                             extensions=json.dumps(insta_data["extensions"]), )
                    curr_batch.save()

                    print(f"process batch {curr_batch.id}...")

                    scraped_edges = 0
                    for edge in insta_data_media["edges"]:
                        process_node(edge["node"], curr_batch)
                        scraped_edges += 1
                        if scraped_edges + scraped_nodes >= scrape_max_nodes:
                            break

                    return {
                        "count": scraped_edges,
                        "next_cursor": insta_data_media["page_info"]["end_cursor"]
                    }

                while (scraped_bates < scrape_max_batches) and (scraped_nodes < scrape_max_nodes):
                    batch_result = process_batch()
                    scraped_nodes += batch_result["count"]
                    scraped_bates += 1
                    next_cursor = batch_result["next_cursor"]

                    print(
                        f"scraped_bates:{scraped_bates} / {scrape_max_batches}, scraped_nodes:{scraped_nodes} / {scrape_max_nodes}\n\n")

                    yield json.dumps({
                        "scraped_bates": scraped_bates,
                        "scraped_nodes": scraped_nodes
                    }) + "\n"

                curr_run.status = "finished"
                curr_run.save()

            except Exception as err:
                curr_run.status = "error"
                curr_run.save()
                yield json.dumps({"! [scraper] error": str(err) + " " + str(traceback.print_exc())}) + "\n"

        response = StreamingHttpResponse(stream_output(), content_type="application/json")
        return response

    except Exception as e:
        return JsonResponse({"! [general] error": str(e) + " " + str(traceback.print_exc())}, status=500)
