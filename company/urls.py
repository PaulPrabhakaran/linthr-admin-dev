from django.urls import path

from . import views

app_name = 'company'

urlpatterns = [
    path('', views.CompanyListView.as_view(), name='company_list'),
    path(
        '<str:company_id>/active/',
        views.CompanyActiveToggleView.as_view(),
        name='company_active',
    ),
    path('<str:company_id>/', views.CompanyDetailView.as_view(), name='company_detail'),
]
