from django.db import models
from django.contrib.auth.models import User

class PIN(models.Model):
    id = models.BigAutoField(primary_key=True)
    entryDate = models.DateTimeField(blank=True, auto_now_add=True)
    expirationDate = models.DateTimeField(blank=True)
    pin = models.IntegerField(blank=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True)