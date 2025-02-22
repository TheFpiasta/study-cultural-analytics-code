import json
import traceback


def extract_keys(input_file, output_file):
    try:
        # Read the input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        extracted_keys = []
        # Extract keys and store them in an array
        for cluster_run in data["data"]:
            for cluster in cluster_run:
                extracted_keys.append(list(cluster.keys())[0])

        # Create a dictionary with a single key containing the array of keys
        output_data = {"count": len(extracted_keys), "keys": extracted_keys}

        # Write the keys array to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4)

        print(f"Successfully extracted {len(extracted_keys)} keys and saved to {output_file}")
        return extracted_keys

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
    input_json = "AI-cluster-combined.json"
    output_json = "AI-cluster-combined-keys.json"

    keys = extract_keys(input_json, output_json)
    if keys:
        print("Extracted keys:", keys)
