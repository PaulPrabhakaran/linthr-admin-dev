"""
URL configuration for linthr_admin project.
"""

from django.contrib import admin
from django.urls import include, path

from accounts.views import home
from company.views import DashboardView

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('companies/', include('company.urls')),
    path('', include('employee.urls')),
]
