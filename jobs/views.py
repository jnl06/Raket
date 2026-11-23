from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import JobForm


from .models import Job


def home(request):
    return render(request, "jobs/home.html")


def post_job(request):
    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            if request.user.is_authenticated:
                job.posted_by = request.user
            job.save()
            messages.success(request, "Your job was posted successfully!")
            return redirect("jobs:home")
    else:
        form = JobForm()

    return render(request, "jobs/postjob.html", {"form": form})


def job_list(request):
    from django.db.models import Q

    jobs = Job.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        jobs = jobs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
        )

    sort = request.GET.get("sort", "newest")
    if sort == "payment_high":
        jobs = jobs.order_by("-estimated_payment", "-created_at")
    elif sort == "payment_low":
        jobs = jobs.order_by("estimated_payment", "-created_at")
    else:
        jobs = jobs.order_by("-created_at")

    return render(request, "jobs/jobs.html", {
        "jobs": jobs,
        "total": jobs.count(),
        "q": q,
        "sort": sort,
    })


def job_detail(request, pk):
    job = Job.objects.filter(pk=pk).first()
    if job is None:
        raise Http404("Job not found")
    return render(request, "jobs/job_detail.html", {"job": job})
