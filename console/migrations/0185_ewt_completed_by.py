# Generated by Django 4.1.3 on 2023-02-08 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0184_remove_ewticket_change_order_remove_ewticket_notes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ewt',
            name='completed_by',
            field=models.CharField(max_length=150, null=True),
        ),
    ]
