# python django

## local python interpreter

```shell
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## start docker

````shell
docker compose up --build --watch
````

## helpfully commands inside of docker

### write packages to requirements.txt

````shell
pip freeze > requirements.txt
````

### run django

````shell
python manage.py runserver
````

### migrate db

````shell
python manage.py migrate
````

### make migrations from models

````shell
python manage.py makemigrations scraper
````

### crate admin user

````shell
python manage.py createsuperuser
````

next: https://docs.djangoproject.com/en/5.1/intro/tutorial03/#use-the-template-system