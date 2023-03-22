from django.db.models import Prefetch, Sum, Count, Q
from django.http import Http404
from django.shortcuts import render
from django.views.generic import DetailView, ListView
from .models import Sheet, Order
from rest_framework import viewsets

from .serializers import SheetSerializer, SheetStatusSerializer


class SheetsListView(ListView):
    model = Sheet
    template_name = 'sheets_to_web/sheet_list.html'
    context_object_name = 'sheets'


def index(request):
    return render(request, 'index.html')


class SheetDetailView(DetailView):
    model = Sheet
    template_name = 'sheets_to_web/sheet_detail.html'
    pk_url_kwarg = 'key'

    def get_queryset(self):
        prefetch_orders = Prefetch('orders', queryset=Order.objects.filter(archieved=False).order_by('row_index'))
        queryset = Sheet.objects.filter(key=self.kwargs.get('key')).prefetch_related(prefetch_orders, 'errors')\
                                .annotate(total_usd=Sum('orders__cost', filter=Q(orders__archieved=False)))\
                                .annotate(total_ruble=Sum('orders__cost_ruble', filter=Q(orders__archieved=False)))\
                                .annotate(errors_count=Count('errors', distinct=True))
        return queryset

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404 as e:
            key = self.kwargs.get('key')
            if len(key) == 44:
                self.model.objects.create(key=key)
                self.object = None
            else:
                raise e
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class SheetViewSet(viewsets.ReadOnlyModelViewSet):

    def get_serializer_class(self):
        status_kwarg = self.request.GET.get('full')
        if status_kwarg:
            return SheetSerializer
        else:
            return SheetStatusSerializer

    def get_queryset(self):
        status_kwarg = self.request.GET.get('full')
        if status_kwarg:
            prefetch_orders = Prefetch('orders', queryset=Order.objects.filter(archieved=False).order_by('row_index'))
            queryset = Sheet.objects.prefetch_related(prefetch_orders, 'errors') \
                .annotate(total_usd=Sum('orders__cost', filter=Q(orders__archieved=False))) \
                .annotate(total_ruble=Sum('orders__cost_ruble', filter=Q(orders__archieved=False))) \
                .annotate(errors_count=Count('errors', distinct=True))
        else:
            queryset = Sheet.objects.all()
        return queryset
