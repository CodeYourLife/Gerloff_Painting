# Generated by Django 4.1.3 on 2022-12-12 00:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0113_alter_changeorders_job_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitems',
            name='wallcovering',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orderitems1', to='console.wallcovering'),
        ),
    ]
