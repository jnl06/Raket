"""Apply, Manage applicants (hire/reject/view resume) and Applied jobs endpoints."""
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from jobs.models import Application, Job

from .serializers import applicant_application_dict, owner_application_dict
from .utils import (
    ApiError,
    api_view,
    choice_filter,
    json_body,
    paginate,
    require_auth,
    require_role,
)
from .views_auth import file_response

PROVIDER = "job_provider"
SEEKER = "job_seeker"
Status = Application.Status

# What a job owner may move an application to, and from which statuses.
OWNER_TRANSITIONS = {
    Status.UNDER_REVIEW: {Status.SUBMITTED},
    Status.HIRED: {Status.SUBMITTED, Status.UNDER_REVIEW, Status.REJECTED},
    Status.REJECTED: {Status.SUBMITTED, Status.UNDER_REVIEW},
}


def _status_counts(qs):
    agg = qs.aggregate(
        total=Count("id"),
        **{s.value: Count("id", filter=Q(status=s.value)) for s in Status},
    )
    return {
        "total": agg["total"],
        "submitted": agg[Status.SUBMITTED],
        "under_review": agg[Status.UNDER_REVIEW],
        "hired": agg[Status.HIRED],
        "rejected": agg[Status.REJECTED],
    }


@api_view("POST")
def apply_to_job(request, job_id):
    user = require_role(request, SEEKER)
    data = json_body(request)
    cover_note = (data.get("cover_note") or "").strip()
    if len(cover_note) > 2000:
        raise ApiError(400, "validation_error", "Cover note is too long.", {"cover_note": ["Max 2000 characters."]})

    with transaction.atomic():
        job = get_object_or_404(Job.objects.select_for_update(), pk=job_id)
        if not job.is_open:  # closed, or its work date has passed
            raise ApiError(409, "job_closed", "This job is no longer accepting applicants.")
        if job.posted_by_id == user.pk:
            raise ApiError(403, "own_job", "You can't apply to your own job post.")
        if Application.objects.filter(job=job, applicant=user).exists():
            raise ApiError(409, "already_applied", "You've already applied to this job.")
        app = Application.objects.create(job=job, applicant=user, cover_note=cover_note)

    app = Application.objects.select_related("job", "job__posted_by", "job__posted_by__profile").get(pk=app.pk)
    return JsonResponse({"application": applicant_application_dict(app)}, status=201)


@api_view("GET")
def my_applications(request):
    """Applied jobs: summary cards, status tabs (with counts), search, list."""
    user = require_role(request, SEEKER)
    base = Application.objects.filter(applicant=user)
    counts = _status_counts(base)

    status = choice_filter(request, "status", Status.choices)
    qs = base.filter(status=status) if status else base
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(job__title__icontains=q)
            | Q(job__location__icontains=q)
            | Q(job__posted_by__profile__full_name__icontains=q)
        )
    qs = qs.select_related("job", "job__posted_by", "job__posted_by__profile").order_by("-created_at", "-id")

    items, meta = paginate(request, qs)
    return JsonResponse(
        {
            "counts": counts,
            "results": [applicant_application_dict(a) for a in items],
            "pagination": meta,
        }
    )


@api_view("GET")
def job_applicants(request, job_id):
    """Manage applicants: applicant cards for one of the owner's posted jobs."""
    user = require_role(request, PROVIDER)
    job = get_object_or_404(Job.objects.with_counts(), pk=job_id)
    if job.posted_by_id != user.pk:
        raise ApiError(403, "not_owner", "You can only view applicants for your own jobs.")

    base = Application.objects.filter(job=job)
    status = choice_filter(request, "status", Status.choices)
    qs = base.filter(status=status) if status else base
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(applicant__profile__full_name__icontains=q)
    qs = qs.select_related("applicant", "applicant__profile").order_by("created_at", "id")

    items, meta = paginate(request, qs, default_size=9)
    return JsonResponse(
        {
            "job": {
                "id": job.pk,
                "title": job.title,
                "status": job.status,
                "number_of_workers": job.number_of_workers,
                "roles_open": max(job.number_of_workers - job.hired_count, 0),
                "applicant_count": job.applicant_count,
            },
            "counts": _status_counts(base),
            "results": [owner_application_dict(a, a.applicant.profile) for a in items],
            "pagination": meta,
        }
    )


@api_view("PATCH", "PUT", "DELETE")
def application_detail(request, application_id):
    if request.method == "DELETE":
        return withdraw(request, application_id)
    return decide(request, application_id)


def decide(request, application_id):
    """Job owner: {"status": "hired" | "rejected" | "under_review"}."""
    user = require_role(request, PROVIDER)
    target = json_body(request).get("status")
    if target not in OWNER_TRANSITIONS:
        raise ApiError(
            400,
            "validation_error",
            "Invalid status.",
            {"status": [f"Choose one of: {', '.join(s.value for s in OWNER_TRANSITIONS)}."]},
        )

    with transaction.atomic():
        app = get_object_or_404(
            Application.objects.select_related("job", "applicant", "applicant__profile"),
            pk=application_id,
        )
        job = Job.objects.select_for_update().get(pk=app.job_id)
        if job.posted_by_id != user.pk:
            raise ApiError(403, "not_owner", "You can only manage applicants of your own jobs.")

        if app.status != target:  # same status again is a no-op (idempotent)
            if app.status not in OWNER_TRANSITIONS[target]:
                raise ApiError(
                    409,
                    "invalid_transition",
                    f"Can't change an application from {app.get_status_display()!r} to {target!r}.",
                )
            if target == Status.HIRED:
                hired = Application.objects.filter(job=job, status=Status.HIRED).count()
                if hired >= job.number_of_workers:
                    raise ApiError(409, "roles_filled", "All roles for this job are already filled.")
                if job.status == Job.Status.CLOSED:
                    raise ApiError(409, "job_closed", "This job is closed.")
            app.status = target
            app.save(update_fields=["status", "updated_at"])
            if target == Status.HIRED and hired + 1 >= job.number_of_workers:
                # Last open role filled: stop accepting applicants.
                job.status = Job.Status.CLOSED
                job.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {
            "application": owner_application_dict(app, app.applicant.profile),
            "job_status": Job.objects.values_list("status", flat=True).get(pk=app.job_id),
        }
    )


def withdraw(request, application_id):
    """Applicant: withdraw an application (not once hired)."""
    user = require_role(request, SEEKER)
    app = get_object_or_404(Application, pk=application_id, applicant=user)
    if app.status == Status.HIRED:
        raise ApiError(409, "already_hired", "You've been hired for this job and can't withdraw here.")
    app.delete()
    return JsonResponse({"ok": True})


@api_view("GET")
def application_resume(request, application_id):
    """Download the applicant's resume. Visible to the job owner and the applicant only.

    When the job owner opens it, a 'submitted' application moves to 'under review'.
    """
    user = require_auth(request)
    app = get_object_or_404(
        Application.objects.select_related("job", "applicant__profile"), pk=application_id
    )
    is_owner = app.job.posted_by_id == user.pk
    if not (is_owner or app.applicant_id == user.pk):
        raise ApiError(403, "forbidden", "You can't view this resume.")
    resume = app.applicant.profile.resume
    if not resume:
        raise ApiError(404, "no_resume", "This applicant hasn't uploaded a resume.")
    if is_owner and app.status == Status.SUBMITTED:
        app.status = Status.UNDER_REVIEW
        app.save(update_fields=["status", "updated_at"])
    return file_response(resume)
