from accounts.session import get_admin_session


def admin_session(request):
    return {'admin_user': get_admin_session(request)}
