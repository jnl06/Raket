from django.http import Http404
from django.shortcuts import render


QUALIFICATIONS = [
    'At least 18 years old.',
    'High school graduate, preferably, but not always required.',
    'Physically fit and capable of lifting and carrying heavy items.',
    'Willing to work under supervision and follow instructions.',
    'Hardworking, reliable, and punctual.',
    'Can work independently or as part of a team.',
    'Willing to work overtime, weekends, or holidays if needed.',
]

HOW_TO_APPLY = (
    'Interested applicants may apply directly to the employer or recruitment agency. '
    'Submit a valid ID and basic personal information. A resume is optional, and previous '
    'work experience is an advantage but not required. Applicants must be physically fit, '
    'willing to perform manual labor, and available on the assigned workday.'
)

JOBS = [
    {
        'id': 1,
        'title': 'Manual Labor and Loading',
        'household': 'Household name',
        'type': 'Part-time',
        'duration': '2 weeks',
        'rate': 1000,
        'category': 'Construction and Building',
        'engagement': 'One-day work, several days, or a project-based contract.',
        'roles_open': 36,
        'qualifications': QUALIFICATIONS,
        'location': 'Lucena, City. Quezon Province',
        'how_to_apply': HOW_TO_APPLY,
        'experience': 'No Formal Experience',
        'city': 'Lucena City',
        'salary_min': 500,
        'salary_max': 900,
        'industry': 'Logistics, Warehouse',
        'date_posted': 'October 9, 2026',
    },
    {
        'id': 2,
        'title': 'Babysitter',
        'household': 'Household name',
        'type': 'Full-time',
        'duration': '1 month',
        'rate': 800,
        'category': 'Household and Care',
        'engagement': 'Several days, or a long-term contract.',
        'roles_open': 5,
        'qualifications': QUALIFICATIONS,
        'location': 'Lucena, City. Quezon Province',
        'how_to_apply': HOW_TO_APPLY,
        'experience': 'Some Experience',
        'city': 'Lucena City',
        'salary_min': 600,
        'salary_max': 800,
        'industry': 'Childcare, Household',
        'date_posted': 'October 12, 2026',
    },
    {
        'id': 3,
        'title': 'House Cleaning',
        'household': 'Household name',
        'type': 'Part-time',
        'duration': '1 week',
        'rate': 600,
        'category': 'Household and Care',
        'engagement': 'One-day work, or several days.',
        'roles_open': 12,
        'qualifications': QUALIFICATIONS,
        'location': 'Lucena, City. Quezon Province',
        'how_to_apply': HOW_TO_APPLY,
        'experience': 'No Formal Experience',
        'city': 'Lucena City',
        'salary_min': 400,
        'salary_max': 600,
        'industry': 'Cleaning, Household',
        'date_posted': 'October 15, 2026',
    },
]


def home(request):
    return render(request, 'home.html')


def post_job(request):
    return render(request, 'jobs/postjob.html')


def job_list(request):
    q = request.GET.get('q', '').strip()
    job_type = request.GET.get('type', 'all')
    duration = request.GET.get('duration', 'all')
    sort = request.GET.get('sort', 'relevance')

    jobs = JOBS

    if q:
        jobs = [j for j in jobs if q.lower() in j['title'].lower()]

    if job_type != 'all':
        jobs = [j for j in jobs if j['type'] == job_type]

    if duration != 'all':
        jobs = [j for j in jobs if j['duration'] == duration]

    if sort == 'rate_high':
        jobs = sorted(jobs, key=lambda j: j['rate'], reverse=True)
    elif sort == 'rate_low':
        jobs = sorted(jobs, key=lambda j: j['rate'])

    context = {
        'jobs': jobs,
        'total': len(JOBS),
        'q': q,
        'job_type': job_type,
        'duration': duration,
        'sort': sort,
        'durations': ['1 week', '2 weeks', '1 month'],
    }

    return render(request, 'jobs.html', context)


def job_detail(request, pk):
    job = next((j for j in JOBS if j['id'] == pk), None)

    if job is None:
        raise Http404('Job not found')

    return render(request, 'job_detail.html', {'job': job})