# Generated by Django 4.1.3 on 2022-12-11 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0094_alter_submittals_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='tm_list',
            name='category',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tm_list',
            name='item',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tm_prices',
            name='category',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tm_prices_master',
            name='category',
            field=models.CharField(default=1, max_length=50),
            preserve_default=False,
        ),
    ]
