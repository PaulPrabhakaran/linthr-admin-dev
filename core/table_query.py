"""Helpers for SSR table list query params (search, status, sort, pagination)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

DEFAULT_PAGE_SIZE = 20
DEFAULT_ORDERING = '-id'


def _coerce_page(value: Any, default: int = 1) -> int:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, page)


def _coerce_page_size(value: Any, default: int = DEFAULT_PAGE_SIZE) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return default
    return min(100, max(1, size))


def parse_list_params(request, *, default_ordering: str = DEFAULT_ORDERING) -> dict[str, Any]:
    get = request.GET
    status = (get.get('status') or 'all').strip().lower()
    if status not in ('all', 'active', 'inactive'):
        status = 'all'
    ordering = (get.get('ordering') or default_ordering).strip() or default_ordering
    return {
        'page': _coerce_page(get.get('page'), 1),
        'page_size': _coerce_page_size(get.get('page_size'), DEFAULT_PAGE_SIZE),
        'search': (get.get('search') or '').strip(),
        'status': status,
        'ordering': ordering,
    }


def query_params(**params: Any) -> dict[str, Any]:
    """Drop empty/default-noise values while always keeping useful list controls."""
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if key == 'status' and value == 'all':
            continue
        if key == 'search' and value == '':
            continue
        if key == 'page' and int(value) == 1:
            continue
        if key == 'page_size' and int(value) == DEFAULT_PAGE_SIZE:
            continue
        cleaned[key] = value
    return cleaned


def build_query(**params: Any) -> str:
    cleaned = query_params(**params)
    return urlencode(cleaned)


def sort_ordering(current: str, field: str) -> str:
    """Toggle asc/desc for a column; switching columns starts at ascending."""
    current = (current or DEFAULT_ORDERING).strip()
    field = field.lstrip('-')
    if current == field:
        return f'-{field}'
    if current == f'-{field}':
        return field
    return field


def sort_state(current: str, field: str) -> str:
    current = (current or '').strip()
    field = field.lstrip('-')
    if current == field:
        return 'asc'
    if current == f'-{field}':
        return 'desc'
    return ''


def pagination_context(
    *,
    count: int,
    page: int,
    page_size: int,
    total_pages: int | None = None,
    search: str = '',
    status: str = 'all',
    ordering: str = DEFAULT_ORDERING,
) -> dict[str, Any]:
    pages = total_pages if total_pages is not None else max(1, (count + page_size - 1) // page_size) if page_size else 1
    page = min(max(1, page), pages) if pages else 1
    base = {
        'search': search,
        'status': status,
        'ordering': ordering,
        'page_size': page_size,
    }
    return {
        'count': count,
        'page': page,
        'page_size': page_size,
        'total_pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_query': build_query(**base, page=page - 1) if page > 1 else '',
        'next_query': build_query(**base, page=page + 1) if page < pages else '',
        'search': search,
        'status': status,
        'ordering': ordering,
        'filter_query': build_query(**{k: v for k, v in base.items() if k != 'status'}),
        'search_query_base': build_query(
            status=status if status != 'all' else None,
            ordering=ordering,
            page_size=page_size,
        ),
    }
