from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile, get_profile

from .forms import JobForm
from .models import Application, Job
from .queries import (
    PUBLIC_SORTS,
    browse_jobs,
    category_counts,
    clean_choice,
    jobs_with_poster,
)

JOBS_PER_PAGE = 10

SORT_LABELS = {
    "relevance": "Relevance",
    "newest": "Newest",
    "pay_high": "Highest pay",
    "pay_low": "Lowest pay",
    "work_date": "Soonest work date",
}


def home(request):
    categories = category_counts()
    # "Popular searches": the categories that actually have open jobs, busiest first.
    popular = [c for c in categories if c["job_count"] > 0][:6]
    latest = list(browse_jobs(sort="newest")[:3])
    return render(
        request,
        "jobs/home.html",
        {
            "popular_categories": popular,
            "categories": categories,
            "latest_jobs": latest,
            "open_jobs_count": sum(c["job_count"] for c in categories),
            "category_choices": Job.Category.choices,
        },
    )


def post_job(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), "accounts:signin")
    if get_profile(request.user).role != Profile.Role.PROVIDER:
        messages.error(request, "Only job provider accounts can post jobs.")
        return redirect("jobs:home")

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, "Your job was posted successfully!")
            return redirect("jobs:job_detail", pk=job.pk)
    else:
        form = JobForm()

    return render(request, "jobs/postjob.html", {"form": form})


def job_list(request):
    params = request.GET
    q = params.get("q", "").strip()
    category = clean_choice(params.get("category"), Job.Category.choices)
    employment_type = clean_choice(params.get("employment_type"), Job.Employment.choices)
    duration = clean_choice(params.get("duration"), Job.Duration.choices)
    sort = params.get("sort", "relevance")
    if sort not in PUBLIC_SORTS or sort not in SORT_LABELS:
        sort = "relevance"

    qs = browse_jobs(
        q=q,
        category=category,
        employment_type=employment_type,
        duration=duration,
        sort=sort,
    )
    page = Paginator(qs, JOBS_PER_PAGE).get_page(params.get("page"))

    # Carry the active filters over to the pagination links.
    active = {
        "q": q,
        "category": category,
        "employment_type": employment_type,
        "duration": duration,
        "sort": sort if sort != "relevance" else "",
    }
    page_query = urlencode({k: v for k, v in active.items() if v})

    # One removable chip per active filter (each link drops just that filter).
    labels = {
        "q": lambda v: f"“{v}”",
        "category": lambda v: dict(Job.Category.choices)[v],
        "employment_type": lambda v: dict(Job.Employment.choices)[v],
        "duration": lambda v: dict(Job.Duration.choices)[v],
    }
    active_filters = []
    for key, label in labels.items():
        if not active[key]:
            continue
        rest = {k: v for k, v in active.items() if v and k != key}
        query = urlencode(rest)
        active_filters.append(
            {
                "label": label(active[key]),
                "remove_url": f"{request.path}?{query}" if query else request.path,
            }
        )

    context = {
        "page": page,
        "jobs": page.object_list,
        "q": q,
        "category": category or "",
        "employment_type": employment_type or "",
        "duration": duration or "",
        "sort": sort,
        "categories": Job.Category.choices,
        "employment_types": Job.Employment.choices,
        "durations": Job.Duration.choices,
        "sorts": list(SORT_LABELS.items()),
        "page_query": page_query,
        "active_filters": active_filters,
        "has_filters": bool(q or category or employment_type or duration),
    }
    return render(request, "jobs/jobs.html", context)


def job_detail(request, pk):
    job = get_object_or_404(jobs_with_poster(), pk=pk)
    user = request.user if request.user.is_authenticated else None

    is_owner = bool(user and job.posted_by_id == user.pk)
    application = (
        Application.objects.filter(job=job, applicant=user).first() if user else None
    )

    # Closed jobs stay visible to their owner and to people who applied (same rule as the API).
    if job.status == Job.Status.CLOSED and not (is_owner or application):
        return render(request, "404.html", status=404)

    if is_owner:
        apply_state = "owner"
    elif application:
        apply_state = "applied"
    elif not job.is_open:
        apply_state = "closed"
    elif user is None:
        apply_state = "anonymous"
    elif get_profile(user).role != Profile.Role.SEEKER:
        apply_state = "provider"
    else:
        apply_state = "can_apply"

    context = {
        "job": job,
        "roles_open": max(job.number_of_workers - job.hired_count, 0),
        "apply_state": apply_state,
        "application": application,
        "is_owner": is_owner,
    }
    return render(request, "jobs/job_detail.html", context)
