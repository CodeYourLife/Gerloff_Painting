from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Submittals)
admin.site.register(SubmittalItems)
admin.site.register(SubmittalNotes)
admin.site.register(SubmittalApprovals)
admin.site.register(SubmittalApprovalNotes)
admin.site.register(SubmittalItemNotes)
