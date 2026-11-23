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
├── jobs/              jobs app (models, shared queries, pages, admin, tests)
│   └── templates/jobs/
├── accounts/          profiles + sign in / sign up / password reset pages
├── api/               JSON API under /api/ (see API.md)
├── templates/         project-wide templates (base.html)
└── static/            project-wide static files
```


## Tests

```bash
python manage.py test
```

## Environment (optional)

`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`0` in production), `DJANGO_ALLOWED_HOSTS`, `RAKET_FRONTEND_URL` (used in password-reset emails).
