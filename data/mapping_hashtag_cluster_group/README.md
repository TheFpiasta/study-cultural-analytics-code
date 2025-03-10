# Process of generating the mapping

We use Anthropic LLM `claude-3-5` to generate the chunks and groups.

1. Django API -> `http://localhost:8000/scraper/generate-tags/` ->  extract for each data point all hashtags and save them
2. Django API -> `http://localhost:8000/scraper/get-hashtags/?chunk-size=100` ->  counts add lists all hashtags. return all hashtags that count matches the given range.
3. Django API -> `http://localhost:8000/scraper/get-chunked/?chunk-size=100` ->  counts add lists all hashtags. Filter all hashtags by there count and the given range. Use the filtered hashtags and generate in the given chunk size chunked groups.
4. Save the JSON for futur optimization to `AI-cluster-combined.json`.
5. Extract all cluster keys as one list with `extract_cluster_keys.py`. This saves the keys to `AI-cluster-combined-keys.json`.
6. Use ``generate_groups.py`` to generate the group to cluster mapping. The result will be saved in `AI-group_cluster.json`.
7. Generate the final hashtags to cluster to group mapping ``mapping.json`` via `create_mapping.py`. 
