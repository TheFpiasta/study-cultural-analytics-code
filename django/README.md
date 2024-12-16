# python django

## get started

### local development

```shell
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

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


next: https://docs.djangoproject.com/en/5.1/intro/tutorial03/