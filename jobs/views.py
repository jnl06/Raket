from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import JobForm


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
