from jobs.models import Jobs
from equipment.models import InventoryNotes, Inventory
import django_filters
from django import forms
from django.db.models import Q


class JobsFilter2(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search4 = django_filters.CharFilter(label='GC =', method='search_filter4')

    def search_filter(self, queryset, name, value):
        return queryset.filter(job_name__icontains=value)

    def search_filter4(self, queryset, name, value):
        return queryset.filter(client__company__icontains=value)

    class Meta:
        model = Jobs
        fields = ['search','search4']



class JobsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name', method='search_filter',
                                       widget=forms.TextInput(attrs={'class': 'form-control'}))

    search2 = django_filters.ChoiceFilter(label="Job Status", method='search_filter2',
                                          choices=((0, "Open Jobs Only"), (1, "All Jobs")),
                                          empty_label="Open Jobs")
    search3 = django_filters.CharFilter(label='Super', method='search_filter3',
                                        widget=forms.TextInput(attrs={'class': 'form-control'}))
    search4 = django_filters.CharFilter(label='GC', method='search_filter4',
                                        widget=forms.TextInput(attrs={'class': 'form-control'}))

    def search_filter(self, queryset, name, value):
        return queryset.filter(job_name__icontains=value)

    def search_filter2(self, queryset, name, value):
        if value == "0":
            return queryset.filter(is_closed=False)
        elif value == "1":
            return queryset.filter()
        else:
            return queryset.filter(is_closed=False)

    def search_filter3(self, queryset, name, value):
        return queryset.filter(
            Q(superintendent__first_name__icontains=value) | Q(superintendent__last_name__icontains=value))

    def search_filter4(self, queryset, name, value):
        return queryset.filter(client__company__icontains=value)

    class Meta:
        model = Jobs
        fields = ['search', 'search2', 'search3', 'search4']


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
