# Raket

A job listing web app built with Django.

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Project layout

```
Raket/                 repo root
├── manage.py
├── requirements.txt
├── Raket/             project package (settings, root urls, wsgi/asgi)
├── jobs/              main app (models, views, urls, admin, tests)
│   └── templates/jobs/
├── templates/         project-wide templates (base.html)
└── static/            project-wide static files
```

