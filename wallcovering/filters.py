from console.models import *
import django_filters

class ChangeOrderFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name= ', method='search_filter')
    def search_filter(self, queryset, name, value):
        return queryset.filter(job_number__job_name__icontains=value)
    class Meta:
        model = ChangeOrders
        fields = ['search']
class OrderItemsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='PO Number=', method='search_filter')
    search2 = django_filters.CharFilter(label='Job Name=', method='search2_filter')
    def search_filter(self, queryset, name, value):
        return queryset.filter(order__po_number=value)
    def search2_filter(self, queryset, name, value):
        return queryset.filter(order__job_number__job_name__icontains=value)
    class Meta:
        model = OrderItems
        fields = ['search','search2']