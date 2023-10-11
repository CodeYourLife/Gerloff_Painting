
from jobs.models import *
from equipment.models import InventoryNotes, Inventory
import django_filters

class JobNotesFilter(django_filters.FilterSet):
    #came from wallcovering.changeorderfilter
    search = django_filters.ChoiceFilter(label="Start Date Notes", method='search_filter2',
                                          choices=((0, "Start Date"), (1, "No")))
    search2 = django_filters.ChoiceFilter(label="Field Notes", method='search_filter3', choices= ((0,"Field Notes"),(1,"No")))


    def search_filter3(self, queryset, name, value):
        if value == "0":
            return queryset.filter(type = "auto_misc_note")
        elif value == "1":
            return queryset.filter()
        else:
            return queryset.filter()

    def search_filter2(self, queryset, name, value):
        if value == "0":
            return queryset.filter(type = "auto_start_date_note")
        elif value == "1":
            return queryset.filter()
        else:
            return queryset.filter()

    class Meta:
        model = JobNotes
        fields = ['search','search2']