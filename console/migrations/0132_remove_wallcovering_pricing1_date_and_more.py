# Generated by Django 4.1.3 on 2022-12-20 02:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0131_wallcoveringpricing'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing1_date',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing1_price',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing1_yards_tier1',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing2_price',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing2_yards_tier1',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing3_price',
        ),
        migrations.RemoveField(
            model_name='wallcovering',
            name='pricing3_yards_tier1',
        ),
    ]
