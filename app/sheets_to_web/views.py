from django.db.models import Prefetch
from django.http import Http404
from django.views.generic import DetailView
from .models import Sheet, Order
import contextlib

# Create your views here.

class SheetDetailView(DetailView):
    model = Sheet
    template_name = 'sheets_to_web/sheet_detail.html'
    pk_url_kwarg = 'key'

    def get_queryset(self):
        prefetch_orders = Prefetch('orders', queryset=Order.objects.order_by('row_index'))
        queryset = Sheet.objects.filter(key=self.kwargs.get('key')).prefetch_related(prefetch_orders)
        return queryset

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            key = self.kwargs.get('key')
            if len(key) == 44:
                self.model.objects.create(key=key)
                self.object = None
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
