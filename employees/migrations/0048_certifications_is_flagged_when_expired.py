from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0047_employeependingactions_subcontractor_employee'),
    ]

    operations = [
        migrations.AddField(
            model_name='certifications',
            name='is_flagged_when_expired',
            field=models.BooleanField(default=True),
        ),
    ]
