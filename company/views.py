import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from accounts.mixins import AdminSessionRequiredMixin
from core.linthr_client import LinthrApiClient, LinthrApiError
from core.table_query import pagination_context, parse_list_params

KOLKATA = ZoneInfo('Asia/Kolkata')


def _company_dashboard_stats(companies: list) -> dict:
    total = len(companies)
    active = sum(1 for c in companies if c.get('active'))
    inactive = total - active
    with_email = sum(1 for c in companies if c.get('email'))
    with_domain = sum(1 for c in companies if c.get('domain'))

    domain_counts: dict[str, int] = {}
    for company in companies:
        domain = (company.get('domain') or '').strip().lower()
        if not domain:
            label = 'No domain'
        else:
            parts = domain.split('.')
            label = parts[-2] if len(parts) >= 2 else domain
            label = label[:18]
        domain_counts[label] = domain_counts.get(label, 0) + 1

    top_domains = sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    domain_labels = [item[0] for item in top_domains]
    domain_values = [item[1] for item in top_domains]
    domain_max = max(domain_values, default=1)
    domain_rows = [
        {
            'label': label,
            'value': value,
            'pct': round((value / domain_max) * 100) if domain_max else 0,
        }
        for label, value in top_domains
    ]

    return {
        'total': total,
        'active': active,
        'inactive': inactive,
        'with_email': with_email,
        'with_domain': with_domain,
        'active_pct': round((active / total) * 100) if total else 0,
        'inactive_pct': round((inactive / total) * 100) if total else 0,
        'email_pct': round((with_email / total) * 100) if total else 0,
        'domain_labels': domain_labels,
        'domain_values': domain_values,
        'domain_rows': domain_rows,
        'domain_chart': {'labels': domain_labels, 'values': domain_values},
        'domains': [
            {'name': row['label'], 'count': row['value'], 'pct': row['pct']}
            for row in domain_rows
        ],
    }


def _parse_created(value):
    if not value:
        return None
    text = str(value).replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KOLKATA)
    return parsed.astimezone(KOLKATA)


def _company_chart(companies, week):
    today = datetime.now(KOLKATA).date()
    monday = today - timedelta(days=today.weekday())
    if week == 'last':
        monday -= timedelta(days=7)
    days = [monday + timedelta(days=offset) for offset in range(5)]
    counts = {day: 0 for day in days}
    for company in companies:
        created = _parse_created(company.get('created_on'))
        if created and created.date() in counts:
            counts[created.date()] += 1
    values = [counts[day] for day in days]
    low = min(values) if values else 0
    high = max(values) if values else 0
    spread = max(4, high - low)
    highlight = len(days) - 1
    if week == 'this':
        for index, day in enumerate(days):
            if day == today:
                highlight = index
                break
    return {
        'labels': [day.strftime('%a') for day in days],
        'values': values,
        'dates': [f"{day.strftime('%a')}, {day.strftime('%b')} {day.day}" for day in days],
        'highlight': highlight,
        'axis_min': max(0, low - spread),
        'axis_max': max(high + max(2, spread // 2), low + 4),
        'pin': True,
        'noun': 'Added',
    }


def _company_board(companies, week='this'):
    stats = _company_dashboard_stats(companies)
    ready = sum(1 for company in companies if company.get('active') and company.get('email'))
    no_email = sum(1 for company in companies if company.get('active') and not company.get('email'))
    inactive = stats['inactive']
    total = stats['total'] or 1

    def share(part):
        return round((part / total) * 100) if stats['total'] else 0

    ordered = sorted(
        companies,
        key=lambda company: _parse_created(company.get('created_on')) or datetime.min.replace(tzinfo=KOLKATA),
        reverse=True,
    )
    activities = []
    for company in ordered[:4]:
        created = _parse_created(company.get('created_on'))
        if created:
            when = f"{created.strftime('%b')} {created.day}, {created.strftime('%I:%M %p')}"
        else:
            when = company.get('domain') or 'Registered'
        name = company.get('name') or 'Company'
        activities.append({
            'kind': 'checkin' if company.get('active') else 'leave',
            'title': f'{name} added',
            'when': when,
        })

    attention = []
    for company in companies:
        if not company.get('id'):
            continue
        if company.get('active') and company.get('email'):
            continue
        name = company.get('name') or 'Company'
        initials = ''.join(part[:1] for part in name.split()[:2]).upper() or 'C'
        if not company.get('active'):
            role = 'Inactive'
            when = 'Needs review'
        else:
            role = company.get('domain') or 'No domain'
            when = 'No email'
        attention.append({
            'name': name,
            'role': role,
            'when': when,
            'initials': initials[:2],
            'id': company.get('id'),
        })

    stats.update({
        'ready': ready,
        'no_email': no_email,
        'ready_pct': share(ready),
        'no_email_pct': share(no_email),
        'chart': _company_chart(companies, week),
        'activities': activities,
        'attention': attention[:4],
    })
    return stats


def _format_registered_at(company: dict) -> dict | None:
    created = _parse_created(company.get('created_at') or company.get('created_on'))
    if not created:
        return None
    return {
        'date': f"{created.strftime('%b')} {created.day}, {created.strftime('%Y')}",
        'time': created.strftime('%I:%M %p').lstrip('0'),
    }


def _enrich_company_row(company: dict) -> dict:
    row = dict(company)
    if row.get('active_employees') is None:
        row['active_employees'] = None
    row['registered_at'] = _format_registered_at(row)
    return row


def _load_company_board(request):
    client = LinthrApiClient()
    companies = []
    error = None
    try:
        companies = [_enrich_company_row(item) for item in client.list_companies()]
    except LinthrApiError as exc:
        error = str(exc)
        messages.error(request, f'Unable to load companies: {exc}')
    return companies, error, _company_dashboard_stats(companies)


class DashboardView(AdminSessionRequiredMixin, View):
    template_name = 'company/dashboard.html'

    def get(self, request):
        week = request.GET.get('week') or 'this'
        if week not in ('this', 'last'):
            week = 'this'
        companies, error, _stats = _load_company_board(request)
        stats = None if error and not companies else _company_board(companies, week)
        return render(
            request,
            self.template_name,
            {
                'stats': stats,
                'error': error,
                'week': week,
            },
        )


class CompanyListView(AdminSessionRequiredMixin, View):
    template_name = 'company/company_list.html'

    def get(self, request):
        params = parse_list_params(request)
        client = LinthrApiClient()
        companies = []
        error = None
        stats = {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'with_email': 0,
            'active_pct': 0,
            'inactive_pct': 0,
            'email_pct': 0,
        }
        page = params['page']
        page_size = params['page_size']
        count = 0
        total_pages = 1
        try:
            payload = client.list_companies_response(
                page=params['page'],
                page_size=params['page_size'],
                search=params['search'],
                status=params['status'],
                ordering=params['ordering'],
            )
            companies = [
                _enrich_company_row(item)
                for item in (
                    payload.get('data')
                    or payload.get('results')
                    or payload.get('companies')
                    or []
                )
            ]
            api_stats = payload.get('stats')
            if isinstance(api_stats, dict) and api_stats:
                stats = {
                    'total': api_stats.get('total', 0),
                    'active': api_stats.get('active', 0),
                    'inactive': api_stats.get('inactive', 0),
                    'with_email': api_stats.get('with_email', 0),
                    'active_pct': api_stats.get('active_pct', 0),
                    'inactive_pct': api_stats.get('inactive_pct', 0),
                    'email_pct': api_stats.get('email_pct', 0),
                }
            else:
                stats = _company_dashboard_stats(companies)
            count = int(payload.get('count', len(companies)) or 0)
            page = int(payload.get('page', params['page']) or params['page'])
            page_size = int(payload.get('page_size', params['page_size']) or params['page_size'])
            total_pages = int(payload.get('total_pages') or 1)
            params['ordering'] = payload.get('ordering') or params['ordering']
            params['status'] = payload.get('status') or params['status']
            params['search'] = payload.get('search') if payload.get('search') is not None else params['search']
        except LinthrApiError as exc:
            error = str(exc)
            messages.error(request, f'Unable to load companies: {exc}')

        pagination = pagination_context(
            count=count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            search=params['search'],
            status=params['status'],
            ordering=params['ordering'],
        )
        return render(
            request,
            self.template_name,
            {
                'companies': companies,
                'error': error,
                'stats': stats,
                'pagination': pagination,
            },
        )


def _empty_company_profile() -> dict:
    return {
        'profile': None,
        'branch_count': 0,
        'mapped_branch_count': 0,
        'department_count': 0,
        'work_schedule_count': 0,
        'holiday_count': 0,
        'male_employee_count': 0,
        'female_employee_count': 0,
        'employee_trend': {
            'labels': [],
            'values': [],
            'dates': [],
            'highlight': 0,
            'delta': 0,
            'delta_label': '0% vs last month',
            'axis_min': 0,
            'axis_max': 8,
            'pin': True,
            'noun': 'Employees',
        },
        'city_count': 0,
        'state_count': 0,
        'cities': [],
        'states': [],
        'branches': [],
        'branch_locations': [],
    }


@method_decorator(require_POST, name='dispatch')
class CompanyActiveToggleView(AdminSessionRequiredMixin, View):
    """Proxy activate/deactivate to the LintHR admin API."""

    def post(self, request, company_id):
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (TypeError, ValueError, UnicodeDecodeError):
            payload = request.POST

        raw_active = payload.get('active') if hasattr(payload, 'get') else None
        if isinstance(raw_active, bool):
            active = raw_active
        elif isinstance(raw_active, str) and raw_active.strip().lower() in (
            'true',
            '1',
            'yes',
            'false',
            '0',
            'no',
        ):
            active = raw_active.strip().lower() in ('true', '1', 'yes')
        else:
            return JsonResponse(
                {'success': False, 'message': "Field 'active' must be a boolean."},
                status=400,
            )

        client = LinthrApiClient()
        try:
            result = client.set_company_active(company_id, active=active)
        except LinthrApiError as exc:
            status_code = exc.status_code or 502
            return JsonResponse(
                {'success': False, 'message': str(exc)},
                status=status_code if 400 <= status_code < 600 else 502,
            )

        data = result.get('data') if isinstance(result, dict) else None
        message = (
            result.get('message')
            if isinstance(result, dict)
            else None
        ) or ('Company activated successfully.' if active else 'Company deactivated successfully.')
        return JsonResponse(
            {
                'success': True,
                'message': message,
                'data': data if isinstance(data, dict) else {'id': company_id, 'active': active},
            }
        )


class CompanyDetailView(AdminSessionRequiredMixin, View):
    template_name = 'company/company_detail.html'

    def get(self, request, company_id):
        week = request.GET.get('week') or 'this'
        if week not in ('this', 'last'):
            week = 'this'
        client = LinthrApiClient()
        company = None
        stats = None
        company_profile = _empty_company_profile()
        error = None
        try:
            companies = client.list_companies()
            company = next(
                (
                    item
                    for item in companies
                    if str(item.get('id')) == str(company_id)
                ),
                None,
            )
            if not company:
                error = 'Company not found.'
                messages.error(request, error)
            else:
                stats = client.get_dashboard(week=week, company_id=company_id)
                try:
                    company_profile = {
                        **_empty_company_profile(),
                        **(client.get_company_profile(company_id) or {}),
                    }
                except LinthrApiError as profile_exc:
                    messages.warning(
                        request,
                        f'Company profile details could not be loaded: {profile_exc}',
                    )
        except LinthrApiError as exc:
            error = str(exc)
            messages.error(request, f'Unable to load company: {exc}')
        return render(
            request,
            self.template_name,
            {
                'company': company,
                'company_id': company_id,
                'stats': stats,
                'company_profile': company_profile,
                'error': error,
                'week': week,
            },
        )
