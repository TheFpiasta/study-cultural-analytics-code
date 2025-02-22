# Process

We use Anthropic LLM `claude-3-5-sonnet-20241022` to generate the chunks and groups.

1. Django API -> `http://localhost:8000/scraper/generate-tags/` ->  extract for each data point all hashtags and save them
2. Django API -> `http://localhost:8000/scraper/get-hashtags/?min-count=1&chunk-size=100&max-count=1` ->  counts add lists all hashtags. return all hashtags that count matches the given range
3. Django API -> `http://localhost:8000/scraper/get-chunked/?min-count=1&chunk-size=100&max-count=1` ->  counts add lists all hashtags. Filter all hashtags by there count and the given range. Use the filtered hashtags and generate in the given chunk size chunked groups.
4. Save the JSON for futur optimization to `data/mapping_hashtag_cluster_group/AI_cluster_[...].json`.
5. Extract all cluster keys as one list with `data/mapping_hashtag_cluster_group/extract_cluster_keys.py`. Save the result to `data/mapping_hashtag_cluster_group/extract_cluster_keys.py`
6. For each 100 cluster keys: generate a grouped list. (via hand, because these are only around 10 prompts to make.) Save all answers to `data/mapping_hashtag_cluster_group/AI-group_cluster.txt` and make the `data/mapping_hashtag_cluster_group/group_cluster.py`
7. Generate the final hashtags to cluster to group mapping json via `data/mapping_hashtag_cluster_group/create_group_cluster_hashtag_mapping.py`
8. Django API -> use the mapping to add clusters and groups to each data entry (and persist them in the db).