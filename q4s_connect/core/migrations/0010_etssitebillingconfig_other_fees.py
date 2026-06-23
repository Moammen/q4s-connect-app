# Generated manually on 2026-06-23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_alter_etssitebillingconfig_delta_t_tolerance'),
    ]

    operations = [
        migrations.AddField(
            model_name='etssitebillingconfig',
            name='other_fees',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=12, null=True),
        ),
    ]
