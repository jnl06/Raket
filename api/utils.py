"""Small helpers shared by every API view (no third-party dependencies)."""
import json
from functools import wraps

from django.core.paginator import EmptyPage, Paginator
from django.http import Http404, JsonResponse

from accounts.models import get_profile


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields

    def response(self):
        body = {"code": self.code, "message": self.message}
        if self.fields:
            body["fields"] = self.fields
        return JsonResponse({"error": body}, status=self.status)


def api_view(*methods):
    """Restrict a view to the given HTTP methods and turn ApiError/Http404 into JSON."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                response = ApiError(
                    405, "method_not_allowed", f"{request.method} is not allowed here."
                ).response()
                response["Allow"] = ", ".join(methods)
                return response
            try:
                return fn(request, *args, **kwargs)
            except ApiError as exc:
                return exc.response()
            except Http404:
                return ApiError(404, "not_found", "Not found.").response()

        return wrapper

    return decorator


def require_auth(request):
    if not request.user.is_authenticated:
        raise ApiError(401, "not_authenticated", "Sign in to continue.")
    return request.user


def require_role(request, role):
    """Require a signed-in user whose profile has `role` (Profile.Role value)."""
    user = require_auth(request)
    profile = get_profile(user)
    if profile.role != role:
        who = "job providers" if role == "job_provider" else "job seekers"
        raise ApiError(403, "wrong_role", f"Only {who} can do this.")
    return user


def json_body(request):
    """Return request data as a dict: JSON bodies, or form/multipart fields."""
    content_type = request.content_type or ""
    if content_type.startswith("application/json"):
        if not request.body:
            return {}
        try:
            data = json.loads(request.body)
        except ValueError:
            raise ApiError(400, "invalid_json", "Request body is not valid JSON.")
        if not isinstance(data, dict):
            raise ApiError(400, "invalid_json", "Request body must be a JSON object.")
        return data
    return request.POST.dict()


def form_errors(form):
    return {
        field: [e["message"] for e in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def validation_error(fields, message="Please fix the highlighted fields."):
    return ApiError(400, "validation_error", message, fields)


def paginate(request, queryset, default_size=10, max_size=50):
    """Paginate with ?page= & ?page_size=. Returns (page_items, meta)."""
    try:
        size = int(request.GET.get("page_size", default_size))
        number = int(request.GET.get("page", 1))
    except ValueError:
        raise ApiError(400, "invalid_pagination", "page and page_size must be integers.")
    size = max(1, min(size, max_size))
    paginator = Paginator(queryset, size)
    try:
        page = paginator.page(max(number, 1))
    except EmptyPage:
        page = paginator.page(paginator.num_pages)
    meta = {
        "count": paginator.count,
        "page": page.number,
        "page_size": size,
        "num_pages": paginator.num_pages,
        "shown": len(page.object_list),
        "has_next": page.has_next(),
        "has_previous": page.has_previous(),
    }
    return list(page.object_list), meta


def choice_filter(request, name, choices):
    """Read an optional ?name=value filter, validating it against `choices`.

    'all' and '' mean "no filter" (matches the 'All types' / 'All durations' dropdowns).
    """
    value = request.GET.get(name, "").strip()
    if value in ("", "all"):
        return None
    if value not in dict(choices):
        raise ApiError(
            400, "invalid_filter", f"Invalid {name}: {value!r}.", {name: ["Invalid choice."]}
        )
    return value
