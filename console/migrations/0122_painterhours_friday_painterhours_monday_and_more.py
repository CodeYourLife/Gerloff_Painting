# Generated by Django 4.1.3 on 2022-12-17 17:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0121_changeorders_materials_used'),
    ]

    operations = [
        migrations.AddField(
            model_name='painterhours',
            name='friday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='monday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='overtime',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='saturday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='sunday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='thursday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='tuesday',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='painterhours',
            name='wednesday',
            field=models.IntegerField(default=0),
        ),
    ]
