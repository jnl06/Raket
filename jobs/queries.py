"""Job queries shared by the JSON API (``api/``) and the server-rendered pages (``jobs/views.py``).

Keeping search / filter / sort rules in one place means the Jobs page and
``GET /api/jobs/`` can never disagree about what a filter means.
"""
from django.db.models import Case, Count, IntegerField, Q, Value, When

from .models import Job

PUBLIC_SORTS = ("relevance", "newest", "oldest", "pay_high", "pay_low", "work_date")

_SORT_ORDER = {
    "relevance": "-created_at",
    "newest": "-created_at",
    "oldest": "created_at",
    "pay_high": "-estimated_payment",
    "pay_low": "estimated_payment",
    "work_date": "work_date",
}


def jobs_with_poster():
    """Every job (open or closed) with its poster and applicant counts preloaded."""
    return Job.objects.select_related("posted_by", "posted_by__profile").with_counts()


def public_jobs():
    """Jobs a visitor may see in listings: active and not yet past."""
    return jobs_with_poster().open_for_applicants()


def search(qs, q):
    return qs.filter(
        Q(title__icontains=q)
        | Q(description__icontains=q)
        | Q(location__icontains=q)
        | Q(industry__icontains=q)
    )


def browse_jobs(
    *,
    q="",
    category=None,
    employment_type=None,
    duration=None,
    location="",
    sort="relevance",
):
    """Public job list. Inputs must already be validated (see ``clean_choice``)."""
    qs = public_jobs()
    if category:
        qs = qs.filter(category=category)
    if employment_type:
        qs = qs.filter(employment_type=employment_type)
    if duration:
        qs = qs.filter(duration=duration)
    if location:
        qs = qs.filter(location__icontains=location)
    if q:
        qs = search(qs, q)

    if sort == "relevance" and q:
        return qs.annotate(
            relevance=Case(
                When(title__icontains=q, then=Value(3)),
                When(location__icontains=q, then=Value(2)),
                When(industry__icontains=q, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("-relevance", "-created_at", "-id")
    return qs.order_by(_SORT_ORDER[sort], "-id")


def category_counts():
    """[{value, label, job_count}] for every category, most open jobs first."""
    counts = dict(
        Job.objects.open_for_applicants()
        .order_by()
        .values_list("category")
        .annotate(n=Count("id"))
    )
    results = [
        {"value": value, "label": label, "job_count": counts.get(value, 0)}
        for value, label in Job.Category.choices
    ]
    results.sort(key=lambda c: (-c["job_count"], c["label"]))
    return results


def clean_choice(value, choices):
    """Return ``value`` if it is one of ``choices`` else None ('all', '' and junk mean no filter)."""
    value = (value or "").strip()
    return value if value in dict(choices) else None
