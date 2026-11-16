from django.shortcuts import redirect
from django.urls import reverse

from accounts.session import (
    clear_admin_session,
    get_admin_session,
    is_admin_authenticated,
    is_admin_verified,
    update_admin_session,
)
from core.linthr_client import LinthrApiClient, LinthrApiError


class AdminSessionMiddleware:
    """
    Gate dashboard pages behind a session established via the linthr login API.
    Unverified admins are sent to the pending page.

    On each protected request, refresh is_verified from LintHrDjango so flipping
    the DB column immediately revokes dashboard access.
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

    def _refresh_verification(self, request) -> bool:
        """Sync session is_verified from live AdminUser. Returns False if identity invalid."""
        session = get_admin_session(request) or {}
        user_uuid = str(session.get('user_uuid') or '').strip()
        if not user_uuid:
            clear_admin_session(request)
            return False

        try:
            me = LinthrApiClient(admin_uuid=user_uuid).get_me()
        except LinthrApiError as exc:
            # Missing / inactive / unknown admin — force re-login.
            if exc.status_code in (401, 403, 404):
                clear_admin_session(request)
                return False
            # Transient API errors: keep existing session flag.
            return True

        update_admin_session(
            request,
            id=me.get('id', session.get('id')),
            user_uuid=me.get('user_uuid', user_uuid),
            email=me.get('email', session.get('email')),
            first_name=me.get('first_name', session.get('first_name', '')),
            last_name=me.get('last_name', session.get('last_name', '')),
            is_verified=bool(me.get('is_verified')),
            is_active=bool(me.get('is_active', True)),
        )
        if me.get('is_active') is False:
            clear_admin_session(request)
            return False
        return True

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
            if not self._refresh_verification(request):
                return redirect('accounts:login')
            if is_admin_verified(request):
                return redirect('dashboard')
            return self.get_response(request)

        if not is_admin_authenticated(request):
            return redirect('accounts:login')

        if not self._refresh_verification(request):
            return redirect('accounts:login')

        if not is_admin_verified(request):
            return redirect('accounts:pending')

        return self.get_response(request)
