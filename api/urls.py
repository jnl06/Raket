from django.urls import path

from . import views_applications as apps
from . import views_auth as auth
from . import views_jobs as jobs

app_name = "api"

urlpatterns = [
    # --- auth & profile ---
    path("auth/csrf/", auth.csrf, name="csrf"),
    path("auth/register/", auth.register, name="register"),
    path("auth/login/", auth.login_view, name="login"),
    path("auth/logout/", auth.logout_view, name="logout"),
    path("auth/password-reset/", auth.password_reset_request, name="password_reset"),
    path("auth/password-reset/confirm/", auth.password_reset_confirm, name="password_reset_confirm"),
    path("me/", auth.me, name="me"),
    path("me/resume/", auth.my_resume, name="my_resume"),
    # --- household: Manage posted jobs ---
    path("me/jobs/", jobs.my_jobs, name="my_jobs"),
    # --- worker: Applied jobs ---
    path("me/applications/", apps.my_applications, name="my_applications"),
    # --- jobs ---
    path("categories/", jobs.categories, name="categories"),
    path("jobs/", jobs.jobs, name="jobs"),
    path("jobs/<int:job_id>/", jobs.job_detail, name="job_detail"),
    path("jobs/<int:job_id>/close/", jobs.close_job, name="job_close"),
    path("jobs/<int:job_id>/repost/", jobs.repost_job, name="job_repost"),
    path("jobs/<int:job_id>/apply/", apps.apply_to_job, name="job_apply"),
    path("jobs/<int:job_id>/applicants/", apps.job_applicants, name="job_applicants"),
    # --- applications ---
    path("applications/<int:application_id>/", apps.application_detail, name="application_detail"),
    path("applications/<int:application_id>/resume/", apps.application_resume, name="application_resume"),
]
