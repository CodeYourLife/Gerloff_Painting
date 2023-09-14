from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Jobs)
admin.site.register(JobNumbers)
admin.site.register(JobNotes)
admin.site.register(Orders)
admin.site.register(OrderItems)
admin.site.register(Clients)
admin.site.register(ClientEmployees)
admin.site.register(Estimates)
admin.site.register(Plans)
admin.site.register(JobCharges)

