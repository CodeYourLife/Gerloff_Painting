from jobs.models import Jobs
from equipment.models import InventoryNotes, Inventory
import django_filters
from django.db.models import Q
from django import forms


class JobsFilter2(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search2 = django_filters.CharFilter(label='Superintendent =', method='search_filter2')
    # search3 = django_filters.filters.BooleanFilter(label='Open Jobs', widget=forms.CheckboxInput,
    #                                                method='search_filter3')
    search4 = django_filters.CharFilter(label='GC =', method='search_filter4')
    search5 = django_filters.filters.BooleanFilter(label='Upcoming Only',widget=forms.CheckboxInput,method='search_filter5')
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
            return queryset.filter(Q(is_labor_done = True)|Q(is_waiting_for_punchlist=True))
        else:
            return queryset.all()

    # def search_filter6(self, queryset, name, value):
    #     if value == True:
    #         return queryset.filter(superintendent=None)
    #     else:
    #         return queryset.all()
    class Meta:
        model = Jobs
        fields = ['search']


class JobsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search2 = django_filters.CharFilter(label='Superintendent =', method='search_filter2')
    search3 = django_filters.filters.BooleanFilter(label='Open Jobs', widget=forms.CheckboxInput,
                                                   method='search_filter3')
    search4 = django_filters.CharFilter(label='GC =', method='search_filter4')
    search5 = django_filters.filters.BooleanFilter(label='Upcoming Only',widget=forms.CheckboxInput,method='search_filter5')
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
            return queryset.filter(Q(is_labor_done = True)|Q(is_waiting_for_punchlist=True))
        else:
            return queryset.all()

    # def search_filter6(self, queryset, name, value):
    #     if value == True:
    #         return queryset.filter(superintendent=None)
    #     else:
    #         return queryset.all()
    class Meta:
        model = Jobs
        fields = ['search']
# class JobsFilter(django_filters.FilterSet):
#     search = django_filters.CharFilter(label='Job Name', method='search_filter',
#                                        widget=forms.TextInput(attrs={'class': 'form-control'}))
#
#     search2 = django_filters.ChoiceFilter(label="Job Status", method='search_filter2',
#                                           choices=((0, "Open Jobs Only"), (1, "All Jobs")),
#                                           empty_label="Open Jobs")
#     search3 = django_filters.CharFilter(label='Super', method='search_filter3',
#                                         widget=forms.TextInput(attrs={'class': 'form-control'}))
#     search4 = django_filters.CharFilter(label='GC', method='search_filter4',
#                                         widget=forms.TextInput(attrs={'class': 'form-control'}))
#
#     def search_filter(self, queryset, name, value):
#         return queryset.filter(job_name__icontains=value)
#
#     def search_filter2(self, queryset, name, value):
#         if value == "0":
#             return queryset.filter(is_closed=False)
#         elif value == "1":
#             return queryset.filter()
#         else:
#             return queryset.filter(is_closed=False)
#
#     def search_filter3(self, queryset, name, value):
#         return queryset.filter(
#             Q(superintendent__first_name__icontains=value) | Q(superintendent__last_name__icontains=value))
#
#     def search_filter4(self, queryset, name, value):
#         return queryset.filter(client__company__icontains=value)
#
#     class Meta:
#         model = Jobs
#         fields = ['search', 'search2', 'search3', 'search4']


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

