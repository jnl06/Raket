from django.urls import path

from . import views, views_manage

app_name = 'jobs'

urlpatterns = [
    path('', views.home, name='home'),
    path('post-job/', views.post_job, name='post_job'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('my-applications/', views_manage.my_applications, name='my_applications'),
    path('my-jobs/', views_manage.my_jobs, name='my_jobs'),
    path('applicants/', views_manage.manage_applicants, name='manage_applicants'),
]
