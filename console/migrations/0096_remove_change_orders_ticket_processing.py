# Generated by Django 4.1.3 on 2022-12-11 14:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0095_tm_list_category_tm_list_item_tm_prices_category_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='change_orders',
            name='ticket_processing',
        ),
    ]
