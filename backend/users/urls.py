from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    AuthViewSet,
    DashboardFunnelView,
    DashboardManagerPerformanceView,
    DashboardRevenueView,
    DashboardSummaryView,
    DealViewSet,
    LeadViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'leads', LeadViewSet, basename='leads')
router.register(r'deals', DealViewSet, basename='deals')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    *router.urls,
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/funnel/', DashboardFunnelView.as_view(), name='dashboard-funnel'),
    path('dashboard/revenue/', DashboardRevenueView.as_view(), name='dashboard-revenue'),
    path('dashboard/manager-performance/', DashboardManagerPerformanceView.as_view(), name='dashboard-manager-performance'),
]
