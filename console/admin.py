from django.contrib import admin

from .models import Jobs, Inventory, Inventory_Type, Employees, Submittals, Rentals, Change_Orders
# Register your models here.
admin.site.register(Inventory)
admin.site.register(Jobs)
admin.site.register(Employees)
admin.site.register(Change_Orders)
admin.site.register(Submittals)
admin.site.register(Rentals)
