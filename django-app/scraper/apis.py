import json
import logging
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

logger = logging.getLogger("django")
logger.setLevel(logging.INFO)


class ScraperStats:
    def __init__(self):
        self.failed_images = 0
        self.node_types = {}
        self.failed_nodes = []

    def on_failed_node(self, node):
        self.failed_nodes.append(node)

    def get_failed_nodes(self):
        return self.failed_nodes

    def reset_failed_nodes(self):
        self.failed_nodes = []

    def on_failed_images(self):
        self.failed_images += 1

    def add_node_type(self, new_node_types):
        if type not in self.node_types:
            self.node_types[new_node_types] = 0
        self.node_types[new_node_types] += 1


@csrf_exempt
def generate_tags(request):
    req_data = []

    if request.method == "GET":
        return JsonResponse({"error": "GET not supportet"}, status=405)

    if request.method == "POST":
        req_data = json.loads(request.body.decode("utf-8"))

    try:
        run_ids = req_data.get("run_ids", [])  # if array empty, all runs will be selected
        print(run_ids)

        if len(run_ids) == 0:
            runs = ScraperRun.objects.all()
        else:
            runs = ScraperRun.objects.filter(id__in=run_ids)

        def stream_output():
            for run in runs:
                print(f"#####\nGenerate Tags for Run {run.name}\n#####")
                all_entries = ScrapeData.objects.filter(scraper_run_id=run.id)
                entry_count = 0

                for entry in all_entries:
                    text = entry.text
                    hashtags = re.findall(r"#(\w+)", text)
                    entry.extracted_hashtags = hashtags
                    entry.save()

                    print(f"{entry.id}: {json.dumps(hashtags)} {entry.type}")
                    entry_count += 1
                    if entry_count % 100 == 0:
                        print(f">>>>>{entry_count} / {len(all_entries)}")
                        yield json.dumps({"status": f"{entry_count} / {len(all_entries)}"})

        response = StreamingHttpResponse(stream_output(), content_type="application/json")
        return response
    except Exception as e:
        print(str(e) + " " + str(traceback.print_exc()))
        return JsonResponse({"! [general] error": str(e) + " " + str(traceback.print_exc())}, status=500)


@csrf_exempt
def start(request):
    req_data = []

    if request.method == "GET":
        return JsonResponse({"error": "GET not supportet"}, status=405)

    if request.method == "POST":
        req_data = json.loads(request.body.decode("utf-8"))

    try:
        scraper_stats = ScraperStats()

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

        # logger.info("create scraper run ...")
        print("create scraper run ...")

        def stream_output():
            try:
                next_cursor = start_cursor

                scraped_bates = 0
                scraped_nodes = 0
                no_error = True
                # date_in_range = True

                dir_ext = re.sub(r'[^a-zA-Z0-9\-]', '', name.lower().replace(" ", "-"))
                img_dir = f"{int(datetime.now().timestamp())}-{dir_ext}"

                img_path = os.path.join(os.getcwd(), 'images', img_dir + "/")
                os.mkdir(img_path)

                if not os.path.exists(img_path):
                    Exception("! [mkdir] img path creation failed for: ", img_path)

                curr_run.img_dir = img_path
                curr_run.save()

                # logger.info("start scraper run ...")
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
                        # logger.info("downloading img ...")
                        print("downloading img ...")
                        img_response = requests.get(img_url)

                        if img_response.status_code == 200:
                            image_content = img_response.content
                            image_type = \
                                img_response.headers.get("Content-Type", "application/octet-stream").split("/")[-1]
                            image_path = f"{img_path}/{img_prefix}.{image_type}"

                            with open(image_path, "wb") as file:
                                file.write(image_content)

                            # logger.info(f"saved img {image_path}")
                            print(f"saved img {image_path}")
                            return f"{img_prefix}.{image_type}"

                        # logger.warning(f"! [img_download]: {img_prefix} failed with status: {img_response.status_code}")
                        print(f"! [img_download]: {img_prefix} failed with status: {img_response.status_code}")
                        scraper_stats.on_failed_images()
                        return False

                    except Exception as d_e:
                        # logger.error(f"! [img_download]: {img_prefix} failed with Exception: ",
                        #       str(d_e) + " " + str(traceback.print_exc()))
                        print(f"! [img_download]: {img_prefix} failed with Exception: ",
                              str(d_e) + " " + str(traceback.print_exc()))
                        return False

                def process_node(node, scrape_batch):
                    try:
                        img_url = node["display_url"]
                        img_name = download_img(img_url, f"{time.time_ns()}_{node["shortcode"]}")

                        # logger.info(f"saving node {node["id"]}...")
                        print(f"saving node {node["id"]}...")
                        scraper_stats.add_node_type(node["__typename"])

                        text = ""
                        if len(node["edge_media_to_caption"]["edges"]) != 0:
                            text = node["edge_media_to_caption"]["edges"][0]["node"]["text"]
                        else:
                            scraper_stats.on_failed_node({"list index edges out of range": node})

                        curr_node = ScrapeData(scraper_run_id=curr_run,
                                               scrape_batch_id=scrape_batch,
                                               node_id=node["id"],
                                               type=node["__typename"],
                                               text=text,
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
                    except Exception as n_e:
                        # node error is not critical to stop scraping
                        scraper_stats.on_failed_node({f"{n_e}": node})
                        print(f"!##### [process node] failed with Exception: ",
                              str(n_e) + " " + str(traceback.print_exc()))

                def process_batch():
                    graphql_url = get_graphql_url(next_cursor)

                    insta_response = requests.get(graphql_url)
                    insta_data = insta_response.json()

                    status = insta_data["status"]
                    curr_batch = ScrapeBatch(scraper_run_id=curr_run,
                                             status=status, )

                    if status != "ok":
                        curr_batch.nodes_in_batch = 0
                        curr_batch.has_next_page = False
                        curr_batch.end_cursor = ""
                        curr_batch.extensions = 0
                        curr_batch.response_on_error = insta_data

                        curr_batch.save()

                        return {
                            "count": 0,
                            "next_cursor": "",
                            "error": True
                        }

                    insta_data_media = insta_data["data"]["user"]["edge_owner_to_timeline_media"]

                    if scraped_bates == 0:
                        update_run_started(insta_data_media["count"])

                    curr_batch = ScrapeBatch(scraper_run_id=curr_run,
                                             nodes_in_batch=len(insta_data_media["edges"]),
                                             has_next_page=insta_data_media["page_info"]["has_next_page"],
                                             end_cursor=insta_data_media["page_info"]["end_cursor"],
                                             status=status,
                                             extensions=json.dumps(insta_data["extensions"]), )
                    curr_batch.save()

                    # logger.info(f"process batch {curr_batch.id}...")
                    print(f"process batch {curr_batch.id}...")
                    scraped_edges = 0
                    for edge in insta_data_media["edges"]:
                        process_node(edge["node"], curr_batch)
                        scraped_edges += 1
                        if scraped_edges + scraped_nodes >= scrape_max_nodes:
                            break

                    if len(scraper_stats.failed_nodes) != 0:
                        # save none critical errors
                        curr_batch.status = "node_errors"
                        curr_batch.response_on_error = scraper_stats.get_failed_nodes()
                        curr_batch.save()
                        scraper_stats.reset_failed_nodes()

                    return {
                        "count": scraped_edges,
                        "next_cursor": insta_data_media["page_info"]["end_cursor"],
                        "error": False
                    }

                while no_error and (scraped_bates < scrape_max_batches) and (scraped_nodes < scrape_max_nodes):
                    batch_result = process_batch()

                    if batch_result["error"]:
                        no_error = False

                    scraped_nodes += batch_result["count"]
                    scraped_bates += 1
                    next_cursor = batch_result["next_cursor"]

                    # logger.info(
                    #     f"scraped_bates:{scraped_bates} / {scrape_max_batches}, scraped_nodes:{scraped_nodes} / {scrape_max_nodes}\n\n")
                    print(
                        f"scraped_bates:{scraped_bates} / {scrape_max_batches}, scraped_nodes:{scraped_nodes} / {scrape_max_nodes}\n\n")

                    yield json.dumps({
                        "scraped_bates": scraped_bates,
                        "scraped_nodes": scraped_nodes
                    }) + "\n"

                if no_error:
                    # logger.info("finished")
                    # logger.info(f"scraped_bates:{scraped_bates}, scraped_nodes:{scraped_nodes}, failed_images: {scraper_stats.failed_images}, types: {scraper_stats.node_types}")
                    print("finished!")
                    curr_run.status = "finished"
                else:
                    curr_run.status = "error"
                    curr_run.error_msg = "graphql batch response error"
                    # logger.warning("finished with error")
                    print("finished with error")

                print(
                    f"scraped_bates:{scraped_bates}, scraped_nodes:{scraped_nodes}, failed_images: {scraper_stats.failed_images}, types: {scraper_stats.node_types}")

                curr_run.save()

            except Exception as err:
                curr_run.status = "error"
                curr_run.error_msg = str(err) + " " + str(traceback.print_exc())
                curr_run.save()
                # logger.error(str(err) + " " + str(traceback.print_exc()))
                print(str(err) + " " + str(traceback.print_exc()))
                yield json.dumps({"! [scraper] error": str(err) + " " + str(traceback.print_exc())}) + "\n"

        response = StreamingHttpResponse(stream_output(), content_type="application/json")
        return response

    except Exception as e:
        # logger.error(str(e) + " " + str(traceback.print_exc()))
        print(str(e) + " " + str(traceback.print_exc()))
        return JsonResponse({"! [general] error": str(e) + " " + str(traceback.print_exc())}, status=500)
