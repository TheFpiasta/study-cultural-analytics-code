import json
import os
import re
import traceback
import anthropic
from dotenv import load_dotenv

load_dotenv()


def split_array(array, chunk_size=100):
    return [array[i:i + chunk_size] for i in range(0, len(array), chunk_size)]


def query_llm(client, prompt):
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
        temperature=1,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )

    response_text = message.content[0].text
    matches = re.findall(r'<answer>(.*?)</answer>', response_text, re.DOTALL)
    result = json.loads(matches[0])

    if "all_group_names" in result:
        del result["all_group_names"]

    return result


def generate_groups(input_file, output_file):
    try:
        # Read the input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        output_data = []
        input_data = data["keys"]
        counter = 0
        while counter < 10 and len(input_data) > 0:
            print(f"Generating group with run {counter}: len(input_data)={len(input_data)}")
            output_data, not_included_clusters = try_to_group_all(input_data, output_data)
            input_data = not_included_clusters
            counter += 1

        cluster_in_groups = 0
        for group in output_data:
            cluster_in_groups += len(group)
        # Write the keys array to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"group_mapping": output_data, "cluster_in_groups":cluster_in_groups, "groups":len(output_data)}, f, indent=4)
    except Exception as e:
        print("An error occurred:" + str(e) + " " + str(traceback.print_exc()))
        return None


def try_to_group_all(data, output_data):
    chunked_data = split_array(data, 50)
    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    default_groups = ["Politics & Government", "Places & Locations", "Environment & Nature", "Social Issues", "Transportation", "Law & Security", "Business & Economy", "Technology & Digital", "Events & Time"]
    f = open("prompt_group_cluster.txt", "r")
    prompt = f.read()
    not_included_clusters = []

    for chunk in chunked_data:
        modified_prompt = prompt.replace("{{STRING_LIST}}", json.dumps(chunk)).replace("{{GROUP_NAMES}}", json.dumps(default_groups))
        res = query_llm(client, modified_prompt)

        res_clusters = []

        for groups in res:
            for cluster in res[groups]:
                if cluster not in chunk:
                    res[groups].remove(cluster)
            res_clusters.extend(res[groups])

        for cluster in chunk:
            if cluster not in res_clusters:
                not_included_clusters.append(cluster)


        if len(res_clusters) != len(chunk):
            print(f"len not matching: is:{len(res_clusters)}, should {len(chunk)} - not_included_clusters:{len(not_included_clusters)}")

        output_data.append(res)
        default_groups = list(set(default_groups) | set(res))
    return output_data, not_included_clusters


# todo note: currently not working! this produces much less cluster in the groups then given as input!
if __name__ == "__main__":
    cluster_json = "AI-cluster-combined-keys.json"
    output_txt = "AI-group_cluster.json"

    generate_groups(cluster_json, output_txt)
