from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(WallcoveringDelivery)
admin.site.register(Wallcovering)
admin.site.register(WallcoveringPricing)
admin.site.register(OutgoingWallcovering)
admin.site.register(OutgoingItem)
admin.site.register(ReceivedItems)
admin.site.register(Packages)


