from console.models import *
from changeorder.models import ChangeOrders
import django_filters
from django.db.models import Q
from wallcovering.models import OrderItems
from django import forms

class ChangeOrderFilter(django_filters.FilterSet):
    search7 = django_filters.filters.BooleanFilter(label='Labor Done', widget=forms.CheckboxInput,method='search_filter7')  # needs to be sent
    search1 = django_filters.filters.BooleanFilter(label='Job Name =',widget=forms.CheckboxInput, method='search_filter')#needs ticket
    search2 = django_filters.CharFilter(label='Superintendent =', method='search_filter2')#super
    search3 = django_filters.filters.BooleanFilter(label='Open Jobs',widget=forms.CheckboxInput,method='search_filter3')#awaiting approval
    search4 = django_filters.filters.BooleanFilter(label='GC =', widget=forms.CheckboxInput,method='search_filter4')#approved
    search5 = django_filters.filters.BooleanFilter(label='Upcoming Only', widget=forms.CheckboxInput,method='search_filter5')#tm only
    search6 = django_filters.filters.BooleanFilter(label='Unassigned',widget=forms.CheckboxInput,method='search_filter6')#include voided

    def search_filter7(self, queryset, name, value):#needs to be sent
        if value == True:
            print("PUMPKIN")
            return queryset.filter(date_sent=None).exclude(Q(is_t_and_m=True) & Q(is_ticket_signed=False))
        else:
            return queryset.all()
    def search_filter(self, queryset, name, value):#needs ticket
        print(value)
        if value == True:
            return queryset.filter(is_t_and_m=True, is_ticket_signed=False,date_sent=None)
        else:
            return queryset.all()
    def search_filter2(self, queryset, name, value):
        if value == 'ALL':
            return queryset.all()
        elif value == 'UNASSIGNED':
            return queryset.filter(job_number__superintendent=None)
        else:
            return queryset.filter(job_number__superintendent__id=value)

    def search_filter3(self, queryset, name, value):#awaiting approval
        if value == True:
            return queryset.filter(is_approved=False).exclude(date_sent=None)
        else:
            return queryset.all()
    def search_filter4(self, queryset, name, value):#approved
        if value == True:
            return queryset.filter(is_approved=True)
        else:
            return queryset.all()
    def search_filter5(self, queryset, name, value):#tm only
        if value == True:
            return queryset.filter(is_t_and_m=True)
        else:
            return queryset.all()

    def search_filter6(self, queryset, name, value):#show voided
        return queryset.all()

    class Meta:
        model = ChangeOrders
        fields = ['search1','search2','search3','search4','search5','search6','search7']
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