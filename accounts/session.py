"""Session helpers for platform admin identity (no local User model)."""

from django.conf import settings


def get_admin_session(request):
    return request.session.get(settings.ADMIN_SESSION_KEY)


def set_admin_session(request, admin_data: dict):
    request.session[settings.ADMIN_SESSION_KEY] = {
        'id': admin_data.get('id'),
        'email': admin_data.get('email'),
        'first_name': admin_data.get('first_name', ''),
        'last_name': admin_data.get('last_name', ''),
        'is_verified': bool(admin_data.get('is_verified')),
        'is_active': bool(admin_data.get('is_active', True)),
    }
    request.session.modified = True


def clear_admin_session(request):
    if settings.ADMIN_SESSION_KEY in request.session:
        del request.session[settings.ADMIN_SESSION_KEY]
        request.session.modified = True


def is_admin_authenticated(request) -> bool:
    data = get_admin_session(request)
    return bool(data and data.get('email'))


def is_admin_verified(request) -> bool:
    data = get_admin_session(request)
    return bool(data and data.get('is_verified'))
