from django.shortcuts import redirect
from django.urls import reverse

from accounts.session import is_admin_authenticated, is_admin_verified


class AdminSessionRequiredMixin:
    """Require an authenticated + verified platform admin session."""

    def dispatch(self, request, *args, **kwargs):
        if not is_admin_authenticated(request):
            return redirect(reverse('accounts:login'))
        if not is_admin_verified(request):
            return redirect(reverse('accounts:pending'))
        return super().dispatch(request, *args, **kwargs)
