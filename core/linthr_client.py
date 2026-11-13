"""HTTP client for calling linthr platform-admin APIs (no local model access)."""

from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


class LinthrApiError(Exception):
    """Raised when a linthr API call fails."""

    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class LinthrApiClient:
    """Talks to linthr using a shared-secret header. Never imports linthr models."""

    def __init__(
        self,
        base_url: str | None = None,
        secret: str | None = None,
        secret_header: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or settings.LINTHR_API_BASE_URL).rstrip('/')
        self.secret = secret if secret is not None else settings.LINTHR_ADMIN_SECRET
        self.secret_header = secret_header or settings.LINTHR_ADMIN_SECRET_HEADER
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        if not self.secret:
            raise LinthrApiError('LINTHR_ADMIN_SECRET is not configured.')
        return {
            self.secret_header: self.secret,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, timeout: int | None = None, **kwargs) -> Any:
        url = f'{self.base_url}{path}'
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(),
                timeout=timeout or self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise LinthrApiError(f'Failed to reach linthr API: {exc}') from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            message = None
            if isinstance(payload, dict):
                message = (
                    payload.get('detail')
                    or payload.get('message')
                    or payload.get('error')
                )
            else:
                message = str(payload)
            raise LinthrApiError(
                message or f'linthr API error ({response.status_code})',
                status_code=response.status_code,
                payload=payload,
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise LinthrApiError('Invalid JSON response from linthr API.') from exc

    def admin_signup(self, id_token: str) -> dict[str, Any]:
        return self._request(
            'POST',
            '/admin-api/auth/google/',
            json={'id_token': id_token},
        )

    def admin_login(self, id_token: str) -> dict[str, Any]:
        return self._request(
            'POST',
            '/admin-api/auth/google/',
            json={'id_token': id_token},
        )

    def admin_logout(self) -> Any:
        return self._request('POST', '/admin-api/auth/logout/', json={})

    def get_dashboard(self, week: str = 'this', company_id: str | int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {'week': week}
        if company_id is not None:
            params['company_id'] = company_id
        data = self._request(
            'GET',
            '/admin-api/dashboard/',
            params=params,
            timeout=90,
        )
        if isinstance(data, dict):
            payload = data.get('data')
            return payload if isinstance(payload, dict) else {}
        return {}

    @staticmethod
    def _list_params(
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        status: str | None = None,
        ordering: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['page_size'] = page_size
        if search:
            params['search'] = search
        if status and status != 'all':
            params['status'] = status
        if ordering:
            params['ordering'] = ordering
        return params

    def list_companies(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        status: str | None = None,
        ordering: str | None = None,
    ) -> list[dict[str, Any]]:
        data = self.list_companies_response(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            ordering=ordering,
        )
        return data.get('data') or data.get('results') or data.get('companies') or []

    def list_companies_response(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        status: str | None = None,
        ordering: str | None = None,
    ) -> dict[str, Any]:
        params = self._list_params(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            ordering=ordering,
        )
        data = self._request('GET', '/admin-api/companies/', params=params or None)
        return data if isinstance(data, dict) else {'data': data or []}

    def get_company_profile(self, company_id: str | int) -> dict[str, Any]:
        data = self._request('GET', f'/admin-api/companies/{company_id}/profile/')
        if isinstance(data, dict):
            payload = data.get('data')
            return payload if isinstance(payload, dict) else {}
        return {}

    def set_company_active(self, company_id: str | int, *, active: bool) -> dict[str, Any]:
        data = self._request(
            'POST',
            f'/admin-api/companies/{company_id}/active/',
            json={'active': bool(active)},
        )
        return data if isinstance(data, dict) else {'success': True, 'data': data or {}}

    def list_employees(
        self,
        company_id: str | int,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        status: str | None = None,
        ordering: str | None = None,
    ) -> list[dict[str, Any]]:
        data = self.get_company_employees_response(
            company_id,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            ordering=ordering,
        )
        return data.get('data') or data.get('results') or data.get('employees') or []

    def get_company_employees_response(
        self,
        company_id: str | int,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        status: str | None = None,
        ordering: str | None = None,
    ) -> dict[str, Any]:
        params = self._list_params(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            ordering=ordering,
        )
        data = self._request(
            'GET',
            f'/admin-api/companies/{company_id}/employees/',
            params=params or None,
        )
        return data if isinstance(data, dict) else {'data': data or []}
