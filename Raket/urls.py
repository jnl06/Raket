"""Root URL configuration for Raket."""
from django.contrib import admin
from django.urls import include, path
from jobs import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('jobs.urls')),
    path("", views.home, name="home"),
    path("jobs/", views.job_list, name="job_list"),
]
