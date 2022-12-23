# Generated by Django 4.1.3 on 2022-12-23 13:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('console', '0133_wallcoveringpricing_note_wallcoveringpricing_unit'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='packages',
            name='description',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='is_all_delivered_to_job',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='order_item1',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='order_item2',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='order_item3',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='order_item4',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='order_item5',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='qnty_item1',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='qnty_item2',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='qnty_item3',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='qnty_item4',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='qnty_item5',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit_item1',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit_item2',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit_item3',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit_item4',
        ),
        migrations.RemoveField(
            model_name='packages',
            name='unit_item5',
        ),
        migrations.AddField(
            model_name='packages',
            name='contents',
            field=models.CharField(max_length=2000, null=True),
        ),
        migrations.AddField(
            model_name='packages',
            name='type',
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='wallcoveringpricing',
            name='min_yards',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='ReceivedItems',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('quantity', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('order_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.orderitems')),
                ('wallcovering_delivery', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='console.wallcoveringdelivery')),
            ],
        ),
    ]
