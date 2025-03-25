# study-cultural-analytics-code

This repository contains code and data for the course Cultural Analytics at the University Leipzig.

## Requirements

Installed Python, Docker and docker-compose.

## Installation

To install the required packages, run:

```bash
cd django-app
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

Go to the `django-app` directory, copy the `.env.example` file to `.env` and fill in the required variables.

```bash
cd django-app
cp .env.example .env
```

To start the Django server, run:

```bash
docker compose up --build --watch
```

The Django server is now running on `http://localhost:8000`.

The Scraper API is available at `http://localhost:8000/scraper`.
The Analyzer is available at `http://localhost:8000/analyzer`.
The Visualizer is available at `http://localhost:8000/visualizer`.

For more helpfully commands, see the [README.md](django-app/README.md) in the `django-app` directory.

To view the database, you can use the included open course [sqlite viewer](data/database/sqlite/sqlite-viewer-gh-pages/index.html).
The source is (https://github.com/inloop/sqlite-viewer).
For more information, see the [README.md](data/database/sqlite/sqlite-viewer-gh-pages/README.md).


More information about the hashtag clustering scrips can be found in this [README.md](data/mapping_hashtag_cluster_group/README.md).
