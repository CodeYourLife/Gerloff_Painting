from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Vehicle)
admin.site.register(RequiredMaintenance)
admin.site.register(VehicleMaintenance)
admin.site.register(VehicleNotes)
