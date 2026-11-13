from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods

from accounts.session import (
    clear_admin_session,
    is_admin_authenticated,
    is_admin_verified,
    set_admin_session,
)
from core.linthr_client import LinthrApiClient, LinthrApiError


def _google_auth_context():
    return {'google_client_id': settings.GOOGLE_CLIENT_ID}


def _handle_google_auth_success(request, payload, success_message: str):
    admin_data = payload.get('data') if isinstance(payload, dict) else None
    if not admin_data:
        messages.error(request, 'Unexpected response from linthr.')
        return None

    set_admin_session(request, admin_data)
    if not admin_data.get('is_verified'):
        messages.info(request, 'Your account is pending verification.')
        return redirect('accounts:pending')

    messages.success(request, success_message)
    return redirect('dashboard')


@require_GET
def home(request):
    if is_admin_authenticated(request):
        if is_admin_verified(request):
            return redirect('dashboard')
        return redirect('accounts:pending')
    return redirect('accounts:login')


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if is_admin_authenticated(request):
            if is_admin_verified(request):
                return redirect('dashboard')
            return redirect('accounts:pending')
        return render(request, self.template_name, _google_auth_context())

    def post(self, request):
        id_token = (request.POST.get('id_token') or '').strip()
        if not id_token:
            messages.error(request, 'Google sign-in failed. Missing id_token.')
            return render(request, self.template_name, _google_auth_context())

        client = LinthrApiClient()
        try:
            payload = client.admin_login(id_token)
        except LinthrApiError as exc:
            messages.error(request, str(exc) or 'Login failed.')
            return render(request, self.template_name, _google_auth_context())

        result = _handle_google_auth_success(request, payload, 'Signed in successfully.')
        if result is None:
            return render(request, self.template_name, _google_auth_context())
        return result


class SignupView(View):
    template_name = 'accounts/signup.html'

    def get(self, request):
        if is_admin_authenticated(request):
            if is_admin_verified(request):
                return redirect('dashboard')
            return redirect('accounts:pending')
        return render(request, self.template_name, _google_auth_context())

    def post(self, request):
        id_token = (request.POST.get('id_token') or '').strip()
        if not id_token:
            messages.error(request, 'Google sign-up failed. Missing id_token.')
            return render(request, self.template_name, _google_auth_context())

        client = LinthrApiClient()
        try:
            payload = client.admin_signup(id_token)
        except LinthrApiError as exc:
            messages.error(request, str(exc) or 'Signup failed.')
            return render(request, self.template_name, _google_auth_context())

        result = _handle_google_auth_success(
            request,
            payload,
            'Account created. Waiting for verification.',
        )
        if result is None:
            return render(request, self.template_name, _google_auth_context())
        return result


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    client = LinthrApiClient()
    try:
        client.admin_logout()
    except LinthrApiError:
        pass
    clear_admin_session(request)
    messages.success(request, 'Signed out.')
    return redirect('accounts:login')


@require_GET
def pending_verification(request):
    if not is_admin_authenticated(request):
        return redirect('accounts:login')
    if is_admin_verified(request):
        return redirect('dashboard')
    return render(request, 'accounts/pending.html')
