import json
import traceback
import group_cluster as gc


def generate_mapping(input_file, output_file):
    try:
        # Read the input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            cluster_hashtags = json.load(f)

        group_cluster_mapping = gc.group_cluster["group_mapping"]

        mapping_group_cluster_hashtag = {}
        mapping_hashtag_cluster_group = {}
        all_hashtags = {}
        all_clusters = {}
        all_groups = {}

        def find_hashtags_in_all_cluster(search_cluster):
            array = cluster_hashtags["data"]
            hashtags = []

            # Iterate through the outer array
            for subarray in array:
                # Iterate through each dictionary in the subarray
                for item in subarray:
                    # Check if the search_key exists in the current dictionary
                    if search_cluster in item:
                        # Append the data associated with the key
                        hashtags.extend(item[search_cluster])

            return hashtags

        def update_reversed_mapping(curr_hashtags, curr_cluster_name, curr_group_name):
            for curr_hashtag in curr_hashtags:
                if curr_hashtag not in mapping_hashtag_cluster_group:
                    mapping_hashtag_cluster_group[curr_hashtag] = {}
                if curr_cluster_name not in mapping_hashtag_cluster_group[curr_hashtag]:
                    mapping_hashtag_cluster_group[curr_hashtag][curr_cluster_name] = []

                mapping_hashtag_cluster_group[curr_hashtag][curr_cluster_name] = list(set(mapping_hashtag_cluster_group[curr_hashtag][curr_cluster_name]) | {curr_group_name} )

        def update_mapping(curr_hashtags, curr_cluster_name, curr_group_name):
            if curr_group_name not in mapping_group_cluster_hashtag:
                mapping_group_cluster_hashtag[curr_group_name] = {}
            if curr_cluster_name not in mapping_group_cluster_hashtag[curr_group_name]:
                mapping_group_cluster_hashtag[curr_group_name][curr_cluster_name] = []

            mapping_group_cluster_hashtag[curr_group_name][curr_cluster_name] = list(set(curr_hashtags) | set(mapping_group_cluster_hashtag[curr_group_name][curr_cluster_name]))

        for group_chunk in group_cluster_mapping:
            for group_name in group_chunk.keys():
                print(f"process group: {group_name} ...")

                clusters = group_chunk[group_name]
                all_groups[group_name] = True

                if group_name not in mapping_group_cluster_hashtag:
                    mapping_group_cluster_hashtag[group_name] = {}

                for cluster_name in clusters:
                    if cluster_name in all_clusters:
                        all_clusters[cluster_name] += 1
                    else:
                        all_clusters[cluster_name] = 1

                    if cluster_name not in mapping_group_cluster_hashtag[group_name]:
                        mapping_group_cluster_hashtag[group_name][cluster_name] = []

                    matching_hashtags = find_hashtags_in_all_cluster(cluster_name)
                    update_reversed_mapping(matching_hashtags, cluster_name, group_name)
                    update_mapping(matching_hashtags, cluster_name, group_name)

                    for hashtag in matching_hashtags:
                        if hashtag[0:5] == "folie":
                            print("hi")
                        all_hashtags[hashtag] = True

        print("Done.")
        # Create result format
        output_data = {"group_count": len(all_groups),
                       "cluster_count": len(all_clusters),
                       "hashtag_count": len(all_hashtags),
                       "mapping": mapping_group_cluster_hashtag,
                       "reversed_mapping": mapping_hashtag_cluster_group,
                       "all_groups": all_groups,
                       "all_clusters": all_clusters,
                       "all_hashtags": all_hashtags}

        # Write the mapping to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{input_file}'")
        return None
    except Exception as e:
        print("An error occurred:" + str(e) + " " + str(traceback.print_exc()))
        return None


if __name__ == "__main__":
    cluster_json = "AI-cluster-combined.json"
    output_json = "mapping.json"

    generate_mapping(cluster_json, output_json)
