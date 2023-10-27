from jobs.models import Jobs
from equipment.models import InventoryNotes, Inventory
import django_filters
from django.db.models import Q


class JobsFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Job Name =', method='search_filter')
    search2 = django_filters.ChoiceFilter(label="Open Jobs Only?", method='search_filter2',
                                          choices=((0, "Open Jobs Only"), (1, "All Jobs")))
    search3 = django_filters.CharFilter(label='Super =', method='search_filter3')

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
        return queryset.filter(Q(superintendent__first_name__icontains=value) | Q(superintendent__last_name__icontains=value))

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
