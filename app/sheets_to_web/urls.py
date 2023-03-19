from django.urls import path

from .views import SheetDetailView

urlpatterns = [
    path('sheet/<key>/', SheetDetailView.as_view(), name='sheet_detail'),
]
