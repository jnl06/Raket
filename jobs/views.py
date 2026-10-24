from django.shortcuts import render


def home(request):
    return render(request, 'jobs/home.html')

def post_job(request):
    return render(request, 'jobs/postjob.html')
