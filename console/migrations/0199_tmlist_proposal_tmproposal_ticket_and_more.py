# Generated by Django 4.1.3 on 2023-02-14 00:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0198_remove_tmlist_notes_tmproposal'),
    ]

    operations = [
        migrations.AddField(
            model_name='tmlist',
            name='proposal',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='console.tmproposal'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tmproposal',
            name='ticket',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='console.ewticket'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='tmlist',
            name='change_order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.changeorders'),
        ),
    ]
