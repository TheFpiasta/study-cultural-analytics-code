FROM python:3.12

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD echo "waiting 5sec to startup db .." && \
    sleep 5 && \
    python manage.py makemigrations scraper && \
    python manage.py migrate && \
    python manage.py runserver 0.0.0.0:8000
#  [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]
#ENTRYPOINT ["top", "-b"]
