from django.shortcuts import redirect
from django.urls import reverse

from accounts.session import get_admin_session, is_admin_authenticated, is_admin_verified


class AdminSessionMiddleware:
    """
    Gate dashboard pages behind a session established via the linthr login API.
    Unverified admins are sent to the pending page.
    """

    EXEMPT_PREFIXES = (
        '/accounts/login/',
        '/accounts/signup/',
        '/accounts/logout/',
        '/admin/',
        '/static/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        request.admin_user = get_admin_session(request)

        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # Allow pending page for authenticated-but-unverified admins
        pending_url = reverse('accounts:pending')
        if path == pending_url:
            if not is_admin_authenticated(request):
                return redirect('accounts:login')
            return self.get_response(request)

        if not is_admin_authenticated(request):
            return redirect('accounts:login')

        if not is_admin_verified(request):
            return redirect('accounts:pending')

        return self.get_response(request)
