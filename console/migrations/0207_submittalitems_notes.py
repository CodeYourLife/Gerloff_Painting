# Generated by Django 4.1.3 on 2023-03-09 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0206_submittalnotes'),
    ]

    operations = [
        migrations.AddField(
            model_name='submittalitems',
            name='notes',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
    ]
