# Generated by Django 4.1.3 on 2022-12-05 23:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0076_remove_incoming_wall_covering_job_number_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Outgoing_Item',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=200, null=True)),
                ('quantity_sent', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Wallcovering_Delivery',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.DeleteModel(
            name='Incoming_Wall_Covering',
        ),
        migrations.RenameField(
            model_name='orders',
            old_name='is_received',
            new_name='is_satisfied',
        ),
        migrations.RemoveField(
            model_name='order_items',
            name='is_received',
        ),
        migrations.RemoveField(
            model_name='outgoing_wallcovering',
            name='date_out',
        ),
        migrations.RemoveField(
            model_name='outgoing_wallcovering',
            name='package_id',
        ),
        migrations.RemoveField(
            model_name='outgoing_wallcovering',
            name='packages_out',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='is_closed',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='job_name',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='package_description',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='wallcovering_id',
        ),
        migrations.AddField(
            model_name='order_items',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.orders'),
        ),
        migrations.AddField(
            model_name='orders',
            name='partial_receipt',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='outgoing_wallcovering',
            name='date',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='packages',
            name='description',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='notes',
            field=models.CharField(max_length=2000, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='order_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.order_items'),
        ),
        migrations.AddField(
            model_name='packages',
            name='quantity_received',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='packages',
            name='unit',
            field=models.CharField(default=1, max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='outgoing_wallcovering',
            name='delivered_by',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='outgoing_wallcovering',
            name='job_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.jobs'),
        ),
        migrations.AlterField(
            model_name='packages',
            name='job_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.jobs'),
        ),
        migrations.AddField(
            model_name='wallcovering_delivery',
            name='items',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.order_items'),
        ),
        migrations.AddField(
            model_name='wallcovering_delivery',
            name='job_number',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.jobs'),
        ),
        migrations.AddField(
            model_name='wallcovering_delivery',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.orders'),
        ),
        migrations.AddField(
            model_name='outgoing_item',
            name='package',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='console.packages'),
        ),
        migrations.AddField(
            model_name='packages',
            name='delivery',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='console.wallcovering_delivery'),
            preserve_default=False,
        ),
    ]
