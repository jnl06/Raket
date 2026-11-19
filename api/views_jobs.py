"""Job endpoints: browse, detail, post, edit, close, repost, manage posted jobs."""
from datetime import date

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from jobs.models import Application, Job

from .forms import JobWriteForm
from .serializers import job_dict
from .utils import (
    ApiError,
    api_view,
    choice_filter,
    form_errors,
    json_body,
    paginate,
    require_role,
    validation_error,
)

PROVIDER = "job_provider"

PUBLIC_SORTS = ("relevance", "newest", "oldest", "pay_high", "pay_low", "work_date")
MANAGE_SORTS = {
    "recent": ("-created_at",),
    "oldest": ("created_at",),
    "work_date": ("work_date", "-created_at"),
    "applicants": ("-applicant_count", "-created_at"),
}


def _jobs():
    return Job.objects.select_related("posted_by", "posted_by__profile").with_counts()


def _search(qs, q):
    return qs.filter(
        Q(title__icontains=q)
        | Q(description__icontains=q)
        | Q(location__icontains=q)
        | Q(industry__icontains=q)
    )


@api_view("GET", "POST")
def jobs(request):
    if request.method == "POST":
        return create_job(request)
    return browse_jobs(request)


def browse_jobs(request):
    """Public job list: search, filters (type/duration/category/location) and sort."""
    qs = _jobs().active().filter(work_date__gte=date.today())

    category = choice_filter(request, "category", Job.Category.choices)
    employment = choice_filter(request, "employment_type", Job.Employment.choices)
    duration = choice_filter(request, "duration", Job.Duration.choices)
    if category:
        qs = qs.filter(category=category)
    if employment:
        qs = qs.filter(employment_type=employment)
    if duration:
        qs = qs.filter(duration=duration)

    location = request.GET.get("location", "").strip()
    if location:
        qs = qs.filter(location__icontains=location)

    q = request.GET.get("q", "").strip()
    if q:
        qs = _search(qs, q)

    sort = request.GET.get("sort", "relevance")
    if sort not in PUBLIC_SORTS:
        raise ApiError(400, "invalid_sort", f"sort must be one of: {', '.join(PUBLIC_SORTS)}.")
    if sort == "relevance" and q:
        qs = qs.annotate(
            relevance=Case(
                When(title__icontains=q, then=Value(3)),
                When(location__icontains=q, then=Value(2)),
                When(industry__icontains=q, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("-relevance", "-created_at")
    else:
        qs = qs.order_by(
            {
                "relevance": "-created_at",
                "newest": "-created_at",
                "oldest": "created_at",
                "pay_high": "-estimated_payment",
                "pay_low": "estimated_payment",
                "work_date": "work_date",
            }[sort],
            "-id",
        )

    items, meta = paginate(request, qs)
    return JsonResponse({"results": [job_dict(j) for j in items], "pagination": meta})


def create_job(request):
    user = require_role(request, PROVIDER)
    data = json_body(request)
    if data.get("confirm") not in (True, "true", "True", "1", "on", 1):
        raise validation_error({"confirm": ["Please confirm the job details are accurate."]})
    form = JobWriteForm.for_payload(data)
    if not form.is_valid():
        raise validation_error(form_errors(form))
    job = form.save(commit=False)
    job.posted_by = user
    job.save()
    return JsonResponse({"job": _detail(job.pk, user)}, status=201)


def _detail(job_id, viewer):
    job = get_object_or_404(_jobs(), pk=job_id)
    mine = None
    if viewer is not None and viewer.is_authenticated:
        mine = Application.objects.filter(job=job, applicant=viewer).first()
    return job_dict(
        job,
        detail=True,
        owner_view=bool(viewer and viewer.is_authenticated and job.posted_by_id == viewer.pk),
        my_application=mine,
        viewer=viewer if viewer and viewer.is_authenticated else None,
    )


@api_view("GET", "PATCH", "PUT")
def job_detail(request, job_id):
    if request.method == "GET":
        job = get_object_or_404(_jobs(), pk=job_id)
        viewer = request.user if request.user.is_authenticated else None
        # Closed jobs stay viewable by their owner and by people who applied.
        if job.status == Job.Status.CLOSED:
            allowed = viewer and (
                job.posted_by_id == viewer.pk
                or Application.objects.filter(job=job, applicant=viewer).exists()
            )
            if not allowed:
                raise ApiError(404, "not_found", "Not found.")
        return JsonResponse({"job": _detail(job_id, viewer)})
    return update_job(request, job_id)


def _owned_job(request, job_id):
    user = require_role(request, PROVIDER)
    job = get_object_or_404(Job, pk=job_id)
    if job.posted_by_id != user.pk:
        raise ApiError(403, "not_owner", "You can only manage your own job posts.")
    return user, job


def update_job(request, job_id):
    user, job = _owned_job(request, job_id)
    form = JobWriteForm.for_payload(json_body(request), instance=job)
    if not form.is_valid():
        raise validation_error(form_errors(form))
    hired = job.applications.filter(status=Application.Status.HIRED).count()
    if form.cleaned_data["number_of_workers"] < hired:
        raise validation_error(
            {"number_of_workers": [f"You've already hired {hired} worker(s)."]}
        )
    form.save()
    return JsonResponse({"job": _detail(job.pk, user)})


@api_view("POST")
def close_job(request, job_id):
    user, job = _owned_job(request, job_id)
    if job.status != Job.Status.CLOSED:
        job.status = Job.Status.CLOSED
        job.save(update_fields=["status", "updated_at"])
    return JsonResponse({"job": _detail(job.pk, user)})


@api_view("POST")
def repost_job(request, job_id):
    """Copy a (usually closed) job into a fresh active post. Body may override fields,
    e.g. {"work_date": "2026-12-01"} — required when the old work date has passed."""
    user, job = _owned_job(request, job_id)
    base = JobWriteForm(instance=job).initial
    payload = {**base, **json_body(request)}
    # Fresh post: apply the "date can't be in the past" rule to the copy.
    form = JobWriteForm(data=payload)
    if not form.is_valid():
        raise validation_error(form_errors(form))
    new_job = form.save(commit=False)
    new_job.posted_by = user
    new_job.status = Job.Status.ACTIVE
    new_job.save()
    return JsonResponse({"job": _detail(new_job.pk, user)}, status=201)


@api_view("GET")
def my_jobs(request):
    """Manage posted jobs: stat cards + searchable/filterable/sortable table."""
    user = require_role(request, PROVIDER)
    base = _jobs().filter(posted_by=user)

    totals = base.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Job.Status.ACTIVE)),
        closed=Count("id", filter=Q(status=Job.Status.CLOSED)),
    )
    stats = {
        "total_jobs": totals["total"],
        "active_jobs": totals["active"],
        "closed_jobs": totals["closed"],
        "total_applicants": Application.objects.filter(job__posted_by=user).count(),
    }

    status = choice_filter(request, "status", Job.Status.choices)
    qs = base.filter(status=status) if status else base
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q))
    sort = request.GET.get("sort", "recent")
    if sort not in MANAGE_SORTS:
        raise ApiError(400, "invalid_sort", f"sort must be one of: {', '.join(MANAGE_SORTS)}.")
    qs = qs.order_by(*MANAGE_SORTS[sort], "-id")

    items, meta = paginate(request, qs)
    return JsonResponse(
        {
            "stats": stats,
            "results": [job_dict(j, owner_view=True) for j in items],
            "pagination": meta,
        }
    )


@api_view("GET")
def categories(request):
    """Category list with open-job counts; most popular first (Home 'Popular searches')."""
    counts = dict(
        Job.objects.active()
        .filter(work_date__gte=date.today())
        .values_list("category")
        .annotate(n=Count("id"))
    )
    results = [
        {"value": value, "label": label, "job_count": counts.get(value, 0)}
        for value, label in Job.Category.choices
    ]
    results.sort(key=lambda c: (-c["job_count"], c["label"]))
    return JsonResponse(
        {
            "results": results,
            "employment_types": [{"value": v, "label": l} for v, l in Job.Employment.choices],
            "durations": [{"value": v, "label": l} for v, l in Job.Duration.choices],
            "schedules": [{"value": v, "label": l} for v, l in Job.Schedule.choices],
            "pay_periods": [{"value": v, "label": l} for v, l in Job.PayPeriod.choices],
        }
    )
