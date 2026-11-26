"""Signed-in pages: Applied jobs (workers), Manage posted jobs and Manage applicants (households).

These pages render the lists on the server. The actions (withdraw, close a job, hire,
reject) call the JSON API from ``static/js/manage.js``.
"""
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile, get_profile

from .models import Application, Job
from .queries import clean_choice, jobs_with_poster

PER_PAGE = 10


def _guard(request, role):
    """None when the visitor may see the page, else the redirect to send them to."""
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "accounts:signin")
    if get_profile(request.user).role != role:
        who = "job seeker" if role == Profile.Role.SEEKER else "job provider"
        messages.error(request, f"That page is only for {who} accounts.")
        return redirect("jobs:home")
    return None


def _status_tabs(base, current, url_name, extra=None):
    """[{value, label, count, active, query}] for All + each application status."""
    counts = base.aggregate(
        total=Count("id"),
        **{s.value: Count("id", filter=Q(status=s.value)) for s in Application.Status},
    )
    tabs = [{"value": "", "label": "All", "count": counts["total"]}]
    tabs += [
        {"value": s.value, "label": s.label, "count": counts[s.value]}
        for s in Application.Status
    ]
    for tab in tabs:
        tab["active"] = tab["value"] == (current or "")
        params = dict(extra or {})
        if tab["value"]:
            params["status"] = tab["value"]
        tab["query"] = "&".join(f"{k}={v}" for k, v in params.items())
    return tabs


def _owner_actions(app):
    """Buttons a job owner can use on an application: [(status, label, style)]."""
    S = Application.Status
    actions = []
    if app.status == S.SUBMITTED:
        actions.append((S.UNDER_REVIEW, "Mark as reviewing", "ghost"))
    if app.status in (S.SUBMITTED, S.UNDER_REVIEW, S.REJECTED) and app.job.status == Job.Status.ACTIVE:
        actions.append((S.HIRED, "Hire", "primary"))
    if app.status in (S.SUBMITTED, S.UNDER_REVIEW):
        actions.append((S.REJECTED, "Not selected", "ghost"))
    return actions


def my_applications(request):
    denied = _guard(request, Profile.Role.SEEKER)
    if denied:
        return denied

    base = Application.objects.filter(applicant=request.user)
    status = clean_choice(request.GET.get("status"), Application.Status.choices)
    qs = base.filter(status=status) if status else base
    qs = qs.select_related("job", "job__posted_by", "job__posted_by__profile")
    page = Paginator(qs, PER_PAGE).get_page(request.GET.get("page"))
    return render(
        request,
        "jobs/my_applications.html",
        {
            "page": page,
            "applications": page.object_list,
            "tabs": _status_tabs(base, status, "jobs:my_applications"),
            "status": status or "",
        },
    )


def my_jobs(request):
    denied = _guard(request, Profile.Role.PROVIDER)
    if denied:
        return denied

    base = jobs_with_poster().filter(posted_by=request.user)
    status = clean_choice(request.GET.get("status"), Job.Status.choices)
    qs = base.filter(status=status) if status else base
    page = Paginator(qs, PER_PAGE).get_page(request.GET.get("page"))
    totals = base.aggregate(
        total=Count("id", distinct=True),
        active=Count("id", filter=Q(status=Job.Status.ACTIVE), distinct=True),
        closed=Count("id", filter=Q(status=Job.Status.CLOSED), distinct=True),
    )
    return render(
        request,
        "jobs/my_jobs.html",
        {
            "page": page,
            "jobs": page.object_list,
            "totals": totals,
            "applicant_total": Application.objects.filter(job__posted_by=request.user).count(),
            "status": status or "",
        },
    )


def manage_applicants(request):
    denied = _guard(request, Profile.Role.PROVIDER)
    if denied:
        return denied

    mine = Job.objects.filter(posted_by=request.user)
    base = Application.objects.filter(job__in=mine)

    job = None
    job_id = request.GET.get("job", "")
    if job_id.isdigit():
        job = mine.filter(pk=int(job_id)).first()
        if job:
            base = base.filter(job=job)

    status = clean_choice(request.GET.get("status"), Application.Status.choices)
    qs = base.filter(status=status) if status else base
    qs = qs.select_related("job", "applicant", "applicant__profile").order_by("created_at", "id")
    page = Paginator(qs, PER_PAGE).get_page(request.GET.get("page"))
    for app in page.object_list:
        app.profile = get_profile(app.applicant)
        app.skills = [x.strip() for x in app.profile.skills.split(",") if x.strip()]
        app.actions = _owner_actions(app)

    extra = {"job": job.pk} if job else {}
    return render(
        request,
        "jobs/applicants.html",
        {
            "page": page,
            "applications": page.object_list,
            "tabs": _status_tabs(base, status, "jobs:manage_applicants", extra),
            "status": status or "",
            "job": job,
            "has_jobs": mine.exists(),
            "page_query": "&".join(
                f"{k}={v}" for k, v in {**extra, **({"status": status} if status else {})}.items()
            ),
        },
    )
