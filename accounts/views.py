"""Sign in / Sign up / password reset pages.

These pages only render the forms. The actual work (creating the account, checking the
password, starting the session) is done by the JSON API in ``api/views_auth.py``, called
from ``static/js/auth.js``.
"""
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def _safe_next(request):
    """The ?next= address, only if it points back at this site."""
    target = request.GET.get('next', '')
    ok = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if ok else ''


def signin(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or 'jobs:home')
    return render(request, 'accounts/signin.html', {'next': next_url})


def signup(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or 'jobs:home')
    role = request.GET.get('role', '')
    return render(
        request,
        'accounts/signup.html',
        {'next': next_url, 'role': role if role in ('job_seeker', 'job_provider') else 'job_seeker'},
    )


def forgot_password(request):
    return render(request, 'accounts/forgot_password.html')


def reset_password(request):
    return render(
        request,
        'accounts/reset_password.html',
        {'uid': request.GET.get('uid', ''), 'token': request.GET.get('token', '')},
    )
