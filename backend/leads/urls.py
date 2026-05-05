from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardFunnelView,
    DashboardManagerPerformanceView,
    DashboardRevenueView,
    DashboardSummaryView,
    LeadViewSet,
)

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='leads')

urlpatterns = [
    *router.urls,
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/funnel/', DashboardFunnelView.as_view(), name='dashboard-funnel'),
    path('dashboard/revenue/', DashboardRevenueView.as_view(), name='dashboard-revenue'),
    path('dashboard/manager-performance/', DashboardManagerPerformanceView.as_view(), name='dashboard-manager-performance'),
]
