from console.models import *
from changeorder.models import ChangeOrders
import django_filters
from django.db.models import Q
from wallcovering.models import OrderItems


class ChangeOrderFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name= ', method='search_filter')
    search2 = django_filters.ChoiceFilter(label="Needs a Ticket Signed?", method='search_filter2', choices= ((0,"Yes"),(1,"No")))

    def search_filter(self, queryset, name, value):
        return queryset.filter(job_number__job_name__icontains=value)


    def search_filter2(self, queryset, name, value):
        if value == "0":
            return queryset.filter(is_t_and_m = True, is_ticket_signed = False, is_closed= False)
        elif value == "1":
            return queryset.filter(Q(is_t_and_m = False) | Q(is_t_and_m = True, is_ticket_signed = True) | Q(is_t_and_m = True, is_closed = True))
        else:
            return queryset.filter()

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