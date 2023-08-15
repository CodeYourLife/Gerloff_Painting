
from jobs.models import Jobs
from equipment.models import InventoryNotes, Inventory
import django_filters

class JobsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Search Job =', method='search_filter')
    def search_filter(self, queryset, name, value):
        return queryset.filter(job_name__icontains=value)
    class Meta:
        model = Jobs
        fields = ['search']

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
        fields = ['search','search2']


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
        fields = ['search','search2', 'search3']