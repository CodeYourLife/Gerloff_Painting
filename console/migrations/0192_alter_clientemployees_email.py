# Generated by Django 4.1.3 on 2023-02-09 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0191_temprecipients_default'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientemployees',
            name='email',
            field=models.EmailField(default=1, max_length=254),
            preserve_default=False,
        ),
    ]