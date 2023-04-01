# Generated by Django 4.1.3 on 2023-03-10 15:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0216_employees_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employees',
            name='level',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='console.employeelevels'),
        ),
        migrations.AlterField(
            model_name='employees',
            name='nickname',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='employees',
            name='phone',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]