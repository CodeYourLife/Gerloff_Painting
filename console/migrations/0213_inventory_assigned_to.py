# Generated by Django 4.1.3 on 2023-03-10 13:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0212_exam_mentorship_productioncategories_trainingtopic_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='assigned_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.employees'),
        ),
    ]
