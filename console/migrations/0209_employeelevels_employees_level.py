# Generated by Django 4.1.3 on 2023-03-09 21:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0208_submittals_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeLevels',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=50)),
                ('pay_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='employees',
            name='level',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='console.employeelevels'),
        ),
    ]