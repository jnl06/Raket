"""Plain functions that turn model instances into JSON-ready dicts."""
from accounts.models import display_name
from jobs.models import Application, Job


def _money(value):
    if value is None:
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _choice(instance, field):
    return {"value": getattr(instance, field), "label": getattr(instance, f"get_{field}_display")()}


def user_dict(user, profile, request=None):
    return {
        "id": user.pk,
        "email": user.email,
        "role": profile.role,
        "full_name": profile.full_name,
        "phone": profile.phone,
        "location": profile.location,
        "bio": profile.bio,
        "skills": [s.strip() for s in profile.skills.split(",") if s.strip()],
        "availability": [
            {"value": v, "label": dict(profile.Availability.choices).get(v, v)}
            for v in profile.availability
        ],
        "has_resume": bool(profile.resume),
        "resume_name": profile.resume.name.rsplit("/", 1)[-1] if profile.resume else None,
        "date_joined": user.date_joined.isoformat(),
    }


def job_dict(job, *, detail=False, owner_view=False, my_application=None, viewer=None):
    """Serialize a Job.

    The queryset should be annotated with `.with_counts()` (applicant_count / hired_count).
    `owner_view` adds applicant counts; `detail` adds the long Job Page fields.
    """
    hired = getattr(job, "hired_count", 0)
    data = {
        "id": job.pk,
        "title": job.title,
        "category": _choice(job, "category"),
        "location": job.location,
        "work_date": job.work_date.isoformat(),
        "work_schedule": _choice(job, "work_schedule"),
        "employment_type": _choice(job, "employment_type"),
        "duration": _choice(job, "duration"),
        "payment": {
            "currency": "PHP",
            "amount": _money(job.estimated_payment),
            "max_amount": _money(job.max_payment),
            "period": job.pay_period,
        },
        "number_of_workers": job.number_of_workers,
        "roles_open": max(job.number_of_workers - hired, 0),
        "status": job.status,
        "household": display_name(job.posted_by),
        "created_at": job.created_at.isoformat(),
    }
    if owner_view:
        data["applicant_count"] = getattr(job, "applicant_count", 0)
        data["hired_count"] = hired
    if detail:
        data.update(
            {
                "description": job.description,
                "requirements": job.requirements,
                "qualifications": [
                    line.strip(" -•\t") for line in job.requirements.splitlines() if line.strip()
                ],
                "experience": job.experience,
                "industry": job.industry,
                "how_to_apply": job.how_to_apply,
                "is_owner": bool(viewer and job.posted_by_id == viewer.pk),
                "my_application": (
                    {
                        "id": my_application.pk,
                        "status": my_application.status,
                        "applied_at": my_application.created_at.isoformat(),
                    }
                    if my_application
                    else None
                ),
            }
        )
    return data


def applicant_application_dict(app):
    """An application as the applicant sees it (Applied jobs screen)."""
    job = app.job
    return {
        "id": app.pk,
        "status": _choice(app, "status"),
        "applied_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
        "cover_note": app.cover_note,
        "job": {
            "id": job.pk,
            "title": job.title,
            "household": display_name(job.posted_by),
            "location": job.location,
            "daily_pay": _money(job.estimated_payment),
            "max_pay": _money(job.max_payment),
            "pay_period": job.pay_period,
            "work_date": job.work_date.isoformat(),
            "status": job.status,
        },
    }


def owner_application_dict(app, profile):
    """An application as the job owner sees it (Manage applicants cards).

    Contact details are only revealed once the applicant is hired.
    """
    hired = app.status == Application.Status.HIRED
    return {
        "id": app.pk,
        "status": _choice(app, "status"),
        "applied_at": app.created_at.isoformat(),
        "cover_note": app.cover_note,
        "applicant": {
            "id": app.applicant_id,
            "name": profile.full_name,
            "location": profile.location,
            "skills": [s.strip() for s in profile.skills.split(",") if s.strip()],
            "availability": [
                {"value": v, "label": dict(profile.Availability.choices).get(v, v)}
                for v in profile.availability
            ],
            "has_resume": bool(profile.resume),
            "email": app.applicant.email if hired else None,
            "phone": profile.phone if hired else None,
        },
    }
