# Generated by Django 4.1.3 on 2022-12-04 20:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0047_clients_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='id',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='console.clients'),
            preserve_default=False,
        ),
    ]
