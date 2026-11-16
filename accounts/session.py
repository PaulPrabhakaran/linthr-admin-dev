"""Session helpers for platform admin identity (no local User model)."""

from django.conf import settings


def get_admin_session(request):
    return request.session.get(settings.ADMIN_SESSION_KEY)


def set_admin_session(request, admin_data: dict):
    request.session.cycle_key()
    request.session[settings.ADMIN_SESSION_KEY] = {
        'id': admin_data.get('id'),
        'user_uuid': str(admin_data.get('user_uuid') or ''),
        'email': admin_data.get('email'),
        'first_name': admin_data.get('first_name', ''),
        'last_name': admin_data.get('last_name', ''),
        'is_verified': bool(admin_data.get('is_verified')),
        'is_active': bool(admin_data.get('is_active', True)),
    }
    request.session.modified = True
    request.session.save()


def update_admin_session(request, **fields):
    """Update cached admin fields without rotating the session key."""
    data = get_admin_session(request)
    if not data:
        return None
    for key, value in fields.items():
        data[key] = value
    if 'user_uuid' in data and data['user_uuid'] is not None:
        data['user_uuid'] = str(data['user_uuid'])
    request.session[settings.ADMIN_SESSION_KEY] = data
    request.session.modified = True
    request.admin_user = data
    return data


def clear_admin_session(request):
    if settings.ADMIN_SESSION_KEY in request.session:
        del request.session[settings.ADMIN_SESSION_KEY]
        request.session.modified = True
        request.session.save()


def is_admin_authenticated(request) -> bool:
    data = get_admin_session(request)
    return bool(data and data.get('user_uuid') and data.get('email'))


def is_admin_verified(request) -> bool:
    data = get_admin_session(request)
    return bool(data and data.get('is_verified'))
