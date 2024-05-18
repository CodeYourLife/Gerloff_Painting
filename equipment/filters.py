from jobs.models import Jobs
from equipment.models import InventoryNotes, Inventory
from rentals.models import Rentals
from subcontractors.models import Subcontracts
import django_filters
from django.db.models import Q
from django import forms

class RentalsFilter(django_filters.FilterSet):
    closed_filter = django_filters.filters.BooleanFilter(label='Show Closed', widget=forms.CheckboxInput,
                                                   method='search_filter')

    def search_filter(self, queryset, name, value):
        if value:
            return queryset.all()
        else:
            return queryset.filter(off_rent_number__isnull = True)

    class Meta:
        model = Rentals
        fields = ['closed_filter']


class JobsFilter2(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search2 = django_filters.CharFilter(label='Superintendent =', method='search_filter2')
    # search3 = django_filters.filters.BooleanFilter(label='Open Jobs', widget=forms.CheckboxInput,
    #                                                method='search_filter3')
    search4 = django_filters.CharFilter(label='GC =', method='search_filter4')
    search5 = django_filters.filters.BooleanFilter(label='Upcoming Only', widget=forms.CheckboxInput,
                                                   method='search_filter5')
    # search6 = django_filters.filters.BooleanFilter(label='Unassigned',widget=forms.CheckboxInput,method='search_filter6')
    search7 = django_filters.filters.BooleanFilter(label='Labor Done', widget=forms.CheckboxInput,
                                                   method='search_filter7')
    search8 = django_filters.filters.BooleanFilter(label='Active Only', widget=forms.CheckboxInput,
                                                   method='search_filter8')
    def search_filter(self, queryset, name, value):
        return queryset.filter(job_name__icontains=value)

    def search_filter2(self, queryset, name, value):
        if value == 'ALL':
            return queryset.all()
        elif value == 'UNASSIGNED':
            return queryset.filter(superintendent=None)
        else:
            return queryset.filter(superintendent__id=value)

    #
    # def search_filter3(self, queryset, name, value):
    #     print("3")
    #     print(value)
    #     return queryset.filter(is_closed=False)
    #
    def search_filter4(self, queryset, name, value):
        return queryset.filter(client__company__icontains=value)

    #
    def search_filter5(self, queryset, name, value):
        if value == True:
            return queryset.filter(is_active=False)
        else:
            return queryset.all()

    def search_filter7(self, queryset, name, value):
        if value == True:
            return queryset.filter(is_waiting_for_punchlist=True)
        else:
            return queryset.all()

    def search_filter8(self, queryset, name, value):
        if value == True:
            return queryset.filter(is_active=True)
        else:
            return queryset.all()

    class Meta:
        model = Jobs
        fields = ['search']


class JobsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search2 = django_filters.CharFilter(label='Superintendent =', method='search_filter2')
    search3 = django_filters.filters.BooleanFilter(label='Open Jobs', widget=forms.CheckboxInput,
                                                   method='search_filter3')
    search4 = django_filters.CharFilter(label='GC =', method='search_filter4')
    search5 = django_filters.filters.BooleanFilter(label='Upcoming Only', widget=forms.CheckboxInput,
                                                   method='search_filter5')
    # search6 = django_filters.filters.BooleanFilter(label='Unassigned',widget=forms.CheckboxInput,method='search_filter6')
    search7 = django_filters.filters.BooleanFilter(label='Labor Done', widget=forms.CheckboxInput,
                                                   method='search_filter7')

    def search_filter(self, queryset, name, value):
        return queryset.filter(job_name__icontains=value)

    def search_filter2(self, queryset, name, value):
        if value == 'ALL':
            return queryset.all()
        elif value == 'UNASSIGNED':
            return queryset.filter(superintendent=None)
        else:
            return queryset.filter(superintendent__id=value)

    def search_filter3(self, queryset, name, value):
        print(value)
        if value == True:
            return queryset.all()
        else:
            return queryset.filter(is_closed=False)

    def search_filter4(self, queryset, name, value):
        return queryset.filter(client__company__icontains=value)

    #
    def search_filter5(self, queryset, name, value):
        if value == True:
            return queryset.filter(is_active=False)
        else:
            return queryset.all()

    def search_filter7(self, queryset, name, value):
        if value == True:
            return queryset.filter(Q(is_labor_done=True) | Q(is_waiting_for_punchlist=True))
        else:
            return queryset.all()

    class Meta:
        model = Jobs
        fields = ['search']

class SubcontractsFilter(django_filters.FilterSet):
    search1 = django_filters.filters.BooleanFilter(label='Show Closed POs', widget=forms.CheckboxInput,
                                                   method='search_filter1')
    search2 = django_filters.filters.BooleanFilter(label='Show Jobs Marked Labor Done', widget=forms.CheckboxInput,
                                                   method='search_filter2')

    def search_filter1(self, queryset, name, value):
        if value == True:
            return queryset.all()
        else:
            return queryset.filter(is_closed=False)

    def search_filter2(self, queryset, name, value):
        if value == True:
            return queryset.filter(job_number__is_labor_done=True)
        else:
            return queryset.all()


    class Meta:
        model = Subcontracts
        fields = ['search1','search2']


class EquipmentNotesFilter(django_filters.FilterSet):
    class Meta:
        model = InventoryNotes
        fields = ['category']


class EquipmentFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Filter By Item =', method='search_filter')
    search2 = django_filters.CharFilter(label='Filter By Number =', method='search2_filter')

    def search_filter(self, queryset, name, value):
        return queryset.filter(item__icontains=value)

    def search2_filter(self, queryset, name, value):
        return queryset.filter(number__icontains=value)

    class Meta:
        model = Inventory
        fields = ['search', 'search2']


class EquipmentFilter2(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Filter By Item =', method='search_filter')
    search2 = django_filters.CharFilter(label='Filter By Number =', method='search2_filter')
    search3 = django_filters.CharFilter(label='Filter By Job =', method='search3_filter')

    def search_filter(self, queryset, name, value):
        return queryset.filter(item__icontains=value)

    def search2_filter(self, queryset, name, value):
        return queryset.filter(number__icontains=value)

    def search3_filter(self, queryset, name, value):
        return queryset.filter(job_number__job_name__icontains=value)

    class Meta:
        model = Inventory
        fields = ['search', 'search2', 'search3']


class EquipmentFilter3(django_filters.FilterSet):
    available_filter = django_filters.filters.BooleanFilter(label='Available', widget=forms.CheckboxInput,
                                                            method='search_filter')
    checked_out_filter = django_filters.filters.BooleanFilter(label='Checked Out', widget=forms.CheckboxInput,
                                                              method='search2_filter')
    missing_filter = django_filters.filters.BooleanFilter(label='Missing', widget=forms.CheckboxInput,
                                                          method='search3_filter')
    ladders_filter = django_filters.filters.BooleanFilter(label='Ladders/Scaffold', widget=forms.CheckboxInput,
                                                          method='search4_filter')
    equipment_filter = django_filters.filters.BooleanFilter(label='Equipment', widget=forms.CheckboxInput,
                                                            method='search5_filter')
    other_filter = django_filters.filters.BooleanFilter(label='Other', widget=forms.CheckboxInput,
                                                        method='search6_filter')

    def search_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter(status='Available')
        else:
            return queryset.all()

    def search2_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter(Q(status='Checked Out')|Q(status='Service'))
        else:
            return queryset.all()

    def search3_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter(status='Missing')
        else:
            return queryset.all()

    def search4_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter(Q(inventory_type__type='Ladder')|Q(inventory_type__type='Scaffold'))
        else:
            return queryset.all()

    def search5_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter(Q(inventory_type__type='Sprayer')|Q(inventory_type__type='Power Washer')|Q(inventory_type__type='Air Compressor'))
        else:
            return queryset.all()

    def search6_filter(self, queryset, name, value):
        if value == True:
            return queryset.filter().exclude(Q(inventory_type__type='Sprayer')|Q(inventory_type__type='Power Washer')|Q(inventory_type__type='Air Compressor')|Q(inventory_type__type='Ladder')|Q(inventory_type__type='Scaffold'))
        else:
            return queryset.all()

    class Meta:
        model = Inventory
        fields = []
