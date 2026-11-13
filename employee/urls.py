from django.urls import path

from . import views

app_name = 'employee'

urlpatterns = [
    path(
        'companies/<str:company_id>/employees/',
        views.EmployeeListView.as_view(),
        name='employee_list',
    ),
]
