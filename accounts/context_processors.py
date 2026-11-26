from .models import Profile


def current_account(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'account_name': '', 'account_role': ''}
    try:
        profile = user.profile
        name, role = profile.full_name, profile.role
    except Profile.DoesNotExist:
        # e.g. an account made with createsuperuser: same fallback as get_profile()
        name = user.get_full_name() or user.get_username()
        role = Profile.Role.PROVIDER if user.is_superuser else Profile.Role.SEEKER
    return {'account_name': name or user.get_username(), 'account_role': role}
