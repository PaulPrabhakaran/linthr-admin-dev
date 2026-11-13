from django import template

from core.table_query import build_query, sort_ordering, sort_state

register = template.Library()


@register.simple_tag
def table_query(pagination, **overrides):
    """Build a query string from current list params with optional overrides."""
    params = {
        'search': pagination.get('search', ''),
        'status': pagination.get('status', 'all'),
        'ordering': pagination.get('ordering', '-id'),
        'page': pagination.get('page', 1),
        'page_size': pagination.get('page_size', 20),
    }
    params.update(overrides)
    query = build_query(**params)
    return f'?{query}' if query else '?'


@register.simple_tag
def sort_query(pagination, field):
    ordering = sort_ordering(pagination.get('ordering', '-id'), field)
    return table_query(pagination, ordering=ordering, page=1)


@register.simple_tag
def sort_class(pagination, field):
    state = sort_state(pagination.get('ordering', '-id'), field)
    if state == 'asc':
        return 'is-sorted is-asc'
    if state == 'desc':
        return 'is-sorted is-desc'
    return ''
