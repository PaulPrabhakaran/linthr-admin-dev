from django.contrib import messages
from django.shortcuts import render
from django.views import View

from accounts.mixins import AdminSessionRequiredMixin
from core.linthr_client import LinthrApiClient, LinthrApiError
from core.table_query import pagination_context, parse_list_params


class EmployeeListView(AdminSessionRequiredMixin, View):
    template_name = 'employee/employee_list.html'

    def get(self, request, company_id):
        params = parse_list_params(request)
        client = LinthrApiClient()
        employees = []
        company = {'id': company_id}
        error = None
        page = params['page']
        page_size = params['page_size']
        count = 0
        total_pages = 1
        people = {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'active_pct': 0,
            'inactive_pct': 0,
            'roles': 0,
            'departments': 0,
            'work_schedules': 0,
            'role_rows': [],
            'role_chart': {'labels': [], 'values': []},
        }
        try:
            payload = client.get_company_employees_response(
                company_id,
                page=params['page'],
                page_size=params['page_size'],
                search=params['search'],
                status=params['status'],
                ordering=params['ordering'],
            )
            if isinstance(payload.get('company'), dict):
                company = payload['company']
            employees = (
                payload.get('data')
                or payload.get('results')
                or payload.get('employees')
                or []
            )
            api_stats = payload.get('stats')
            if isinstance(api_stats, dict) and api_stats:
                people = {
                    'total': api_stats.get('total', 0),
                    'active': api_stats.get('active', 0),
                    'inactive': api_stats.get('inactive', 0),
                    'active_pct': api_stats.get('active_pct', 0),
                    'inactive_pct': api_stats.get('inactive_pct', 0),
                    'roles': api_stats.get('roles', 0),
                    'departments': api_stats.get('departments', 0),
                    'work_schedules': api_stats.get('work_schedules', 0),
                    'role_rows': api_stats.get('role_rows') or [],
                    'role_chart': api_stats.get('role_chart')
                    or {'labels': [], 'values': []},
                }
            else:
                active_count = sum(
                    1
                    for employee in employees
                    if employee.get('active') or employee.get('is_active')
                )
                total = len(employees)
                inactive_count = total - active_count
                role_counts: dict[str, int] = {}
                for employee in employees:
                    role = employee.get('role') or employee.get('designation') or 'Unassigned'
                    role = str(role).strip()[:28] or 'Unassigned'
                    role_counts[role] = role_counts.get(role, 0) + 1
                top_roles = sorted(
                    role_counts.items(), key=lambda item: (-item[1], item[0])
                )[:5]
                role_max = max((item[1] for item in top_roles), default=1)
                role_rows = [
                    {
                        'label': label,
                        'value': value,
                        'pct': round((value / role_max) * 100) if role_max else 0,
                        'share': round((value / total) * 100) if total else 0,
                    }
                    for label, value in top_roles
                ]
                people = {
                    'total': total,
                    'active': active_count,
                    'inactive': inactive_count,
                    'active_pct': round((active_count / total) * 100) if total else 0,
                    'inactive_pct': round((inactive_count / total) * 100) if total else 0,
                    'roles': len(role_counts),
                    'departments': 0,
                    'work_schedules': 0,
                    'role_rows': role_rows,
                    'role_chart': {
                        'labels': [item[0] for item in top_roles],
                        'values': [item[1] for item in top_roles],
                    },
                }
            count = int(payload.get('count', len(employees)) or 0)
            page = int(payload.get('page', params['page']) or params['page'])
            page_size = int(
                payload.get('page_size', params['page_size']) or params['page_size']
            )
            total_pages = int(payload.get('total_pages') or 1)
            params['ordering'] = payload.get('ordering') or params['ordering']
            params['status'] = payload.get('status') or params['status']
            if payload.get('search') is not None:
                params['search'] = payload.get('search')
        except LinthrApiError as exc:
            error = str(exc)
            messages.error(request, f'Unable to load employees: {exc}')

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
                'company': company,
                'company_id': company_id,
                'employees': employees,
                'active_count': people['active'],
                'people': people,
                'error': error,
                'pagination': pagination,
            },
        )
