# Generated by Django 4.1.3 on 2023-03-24 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0240_productioncategory'),
    ]

    operations = [
        migrations.AddField(
            model_name='productionitems',
            name='team_members',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
