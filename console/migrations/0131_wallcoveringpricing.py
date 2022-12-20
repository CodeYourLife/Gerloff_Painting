# Generated by Django 4.1.3 on 2022-12-20 02:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0130_packages_is_all_delivered_to_job'),
    ]

    operations = [
        migrations.CreateModel(
            name='WallcoveringPricing',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('quote_date', models.DateField()),
                ('min_yards', models.IntegerField(blank=True)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('wallcovering', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.wallcovering')),
            ],
        ),
    ]
