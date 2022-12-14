# Generated by Django 4.1.3 on 2022-12-04 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0042_alter_checklist_job_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobs',
            name='client',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Co_Contact',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Co_Email',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Pm',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Pm_Email',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Pm_Phone',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Submittal_Contact',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Submittal_Email',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Super',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Super_Email',
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='jobs',
            name='client_Super_Phone',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
