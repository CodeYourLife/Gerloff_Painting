# Generated by Django 4.1.3 on 2022-12-11 20:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0107_remove_packages_job_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='packages',
            name='order_item',
        ),
        migrations.AddField(
            model_name='outgoing_item',
            name='outgoing_event',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='console.outgoing_wallcovering'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item1', to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item2', to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item3',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item3', to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item4',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item4', to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item5',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_item5', to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='qnty_item1',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='qnty_item2',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='qnty_item3',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='qnty_item4',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='qnty_item5',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit_item1',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit_item2',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit_item3',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit_item4',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit_item5',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='outgoing_item',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='console.packages'),
        ),
    ]
