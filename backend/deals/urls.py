from rest_framework.routers import DefaultRouter

from .views import DealViewSet

router = DefaultRouter()
router.register(r'deals', DealViewSet, basename='deals')

urlpatterns = [
    *router.urls,
]
