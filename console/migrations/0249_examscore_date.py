# Generated by Django 4.1.3 on 2023-03-27 17:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0248_classattendees_student2_alter_classattendees_student'),
    ]

    operations = [
        migrations.AddField(
            model_name='examscore',
            name='date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
