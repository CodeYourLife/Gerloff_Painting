# Generated by Django 4.1.3 on 2022-12-15 17:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0119_changeorders_date_week_ending'),
    ]

    operations = [
        migrations.AddField(
            model_name='changeorders',
            name='ticket_description',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
        migrations.CreateModel(
            name='PainterHours',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('details', models.CharField(max_length=2000)),
                ('cop_number', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.changeorders')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.employees')),
            ],
        ),
    ]
