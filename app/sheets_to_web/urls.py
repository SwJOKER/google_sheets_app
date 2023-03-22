from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework import routers

from .views import SheetDetailView, SheetsListView, index, SheetViewSet

router = routers.DefaultRouter()

router.register(r'sheets', SheetViewSet, basename='sheets')

urlpatterns = [
    path('', RedirectView.as_view(url='/sheet/')),
    path('sheets/<key>/', SheetDetailView.as_view(), name='sheet_detail'),
    path('sheets/', SheetsListView.as_view(), name='sheets_list'),
    path('api/', include(router.urls)),
    path('', index),
]
