"""Sign up / Log in / profile / resume endpoints."""
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie

from accounts.models import Profile, get_profile

from .serializers import user_dict
from .utils import ApiError, api_view, json_body, require_auth, validation_error

User = get_user_model()
PHONE_RE = re.compile(r"^\+?\d[\d\s-]{6,17}$")
TRUE_VALUES = (True, "true", "True", "1", "on", 1)


def _me(user):
    return user_dict(user, get_profile(user))


@ensure_csrf_cookie
@api_view("GET")
def csrf(request):
    """Call once on page load; sets the csrftoken cookie. Send it back as X-CSRFToken."""
    return JsonResponse({"csrfToken": get_token(request)})


@api_view("POST")
def register(request):
    data = json_body(request)
    errors = {}

    role = data.get("role", Profile.Role.SEEKER)
    if role not in Profile.Role.values:
        errors["role"] = ["Choose Job Seeker or Job Provider."]

    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        errors["full_name"] = ["Enter your full name."]
    elif len(full_name) > 150:
        errors["full_name"] = ["Name is too long."]

    email = (data.get("email") or "").strip().lower()
    try:
        validate_email(email)
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(
            email__iexact=email
        ).exists():
            errors["email"] = ["An account with this email already exists."]
    except ValidationError:
        errors["email"] = ["Enter a valid email address."]

    phone = (data.get("phone") or "").strip()
    if not phone:
        errors["phone"] = ["Enter your phone number."]
    elif not PHONE_RE.match(phone):
        errors["phone"] = ["Enter a valid phone number."]

    password = data.get("password") or ""
    if data.get("confirm_password") != password:
        errors["confirm_password"] = ["Passwords do not match."]
    if password:
        try:
            validate_password(password, user=User(username=email, email=email))
        except ValidationError as exc:
            errors["password"] = list(exc.messages)
    else:
        errors["password"] = ["Create a password."]

    if data.get("agree_terms") not in TRUE_VALUES:
        errors["agree_terms"] = ["You must agree to the Terms of Service and Privacy Policy."]

    if errors:
        raise validation_error(errors)

    with transaction.atomic():
        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=full_name[:150]
        )
        Profile.objects.create(user=user, role=role, full_name=full_name, phone=phone)
    login(request, user)
    return JsonResponse({"user": _me(user)}, status=201)


@api_view("POST")
def login_view(request):
    data = json_body(request)
    identifier = (data.get("email") or "").strip()
    password = data.get("password") or ""
    errors = {}
    if not identifier:
        errors["email"] = ["Enter your email address."]
    if not password:
        errors["password"] = ["Enter your password."]
    if errors:
        raise validation_error(errors)

    # Sign in with email; fall back to username so accounts made via createsuperuser work.
    match = User.objects.filter(email__iexact=identifier).first()
    user = authenticate(request, username=match.get_username() if match else identifier, password=password)
    if user is None:
        raise ApiError(401, "invalid_credentials", "Incorrect email or password.")

    login(request, user)
    if data.get("remember_me") not in TRUE_VALUES:
        request.session.set_expiry(0)  
    return JsonResponse({"user": _me(user)})


@api_view("POST")
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


def _validate_resume(upload):
    ext = Path(upload.name).suffix.lower()
    if ext not in settings.RESUME_ALLOWED_EXTENSIONS:
        raise validation_error({"resume": ["Upload a PDF or Word document (.pdf, .doc, .docx)."]})
    if upload.size > settings.RESUME_MAX_BYTES:
        mb = settings.RESUME_MAX_BYTES // (1024 * 1024)
        raise validation_error({"resume": [f"Resume must be {mb} MB or smaller."]})


@api_view("GET", "PATCH", "POST")
def me(request):
    user = require_auth(request)
    profile = get_profile(user)
    if request.method == "GET":
        return JsonResponse({"user": user_dict(user, profile)})

    data = json_body(request)
    errors = {}
    if "full_name" in data:
        name = (data["full_name"] or "").strip()
        if not name:
            errors["full_name"] = ["Name can't be empty."]
        else:
            profile.full_name = name[:150]
            user.first_name = name[:150]
    if "phone" in data:
        phone = (data["phone"] or "").strip()
        if phone and not PHONE_RE.match(phone):
            errors["phone"] = ["Enter a valid phone number."]
        profile.phone = phone
    for field, limit in (("location", 150), ("bio", 2000), ("skills", 300)):
        if field in data:
            value = data[field]
            if isinstance(value, list):  # skills may be sent as a list
                value = ", ".join(str(v).strip() for v in value if str(v).strip())
            setattr(profile, field, (value or "").strip()[:limit])
    if "availability" in data:
        value = data["availability"]
        if isinstance(value, str):
            value = [v for v in value.split(",") if v]
        if not isinstance(value, list) or any(v not in Profile.Availability.values for v in value):
            errors["availability"] = [
                f"Choose from: {', '.join(Profile.Availability.values)}."
            ]
        else:
            profile.availability = sorted(set(value))
    upload = request.FILES.get("resume")
    if upload:
        _validate_resume(upload)
    if errors:
        raise validation_error(errors)

    if upload:
        if profile.resume:
            profile.resume.delete(save=False)
        profile.resume = upload
    elif data.get("remove_resume") in TRUE_VALUES and profile.resume:
        profile.resume.delete(save=False)
        profile.resume = ""
    with transaction.atomic():
        user.save()
        profile.save()
    return JsonResponse({"user": user_dict(user, profile)})


@api_view("GET")
def my_resume(request):
    profile = get_profile(require_auth(request))
    if not profile.resume:
        raise Http404
    return file_response(profile.resume)


def file_response(field_file):
    try:
        handle = field_file.open("rb")
    except FileNotFoundError:
        raise Http404
    return FileResponse(handle, filename=field_file.name.rsplit("/", 1)[-1])


# ---- Forgot password ------------------------------------------------------

@api_view("POST")
def password_reset_request(request):
    """Always answers 200 so it can't be used to discover which emails have accounts."""
    email = (json_body(request).get("email") or "").strip()
    if not email:
        raise validation_error({"email": ["Enter your email address."]})
    for user in User.objects.filter(email__iexact=email, is_active=True):
        if not user.has_usable_password():
            continue
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/?uid={uid}&token={token}"
        send_mail(
            "Reset your Raket password",
            f"Use this link to choose a new password:\n\n{link}\n\n"
            "If you didn't ask for this, you can ignore this email.",
            None,
            [user.email],
        )
    return JsonResponse({"ok": True})


@api_view("POST")
def password_reset_confirm(request):
    data = json_body(request)
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(data.get("uid", ""))))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is None or not default_token_generator.check_token(user, data.get("token", "")):
        raise ApiError(400, "invalid_token", "This reset link is invalid or has expired.")
    password = data.get("new_password") or ""
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise validation_error({"new_password": list(exc.messages)})
    user.set_password(password)
    user.save()
    return JsonResponse({"ok": True})
