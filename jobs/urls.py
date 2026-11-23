from django.urls import path

from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.home, name='home'),
    path('post-job/', views.post_job, name='post_job'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
]
