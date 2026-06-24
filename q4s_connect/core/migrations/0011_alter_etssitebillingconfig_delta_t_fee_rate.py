from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_etssitebillingconfig_other_fees'),
    ]

    operations = [
        # Clear old values (e.g. 15.0, 10.0) that don't fit the new precision
        migrations.RunSQL(
            "UPDATE core_ets_site_billing_config SET delta_t_fee_rate = NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='etssitebillingconfig',
            name='delta_t_fee_rate',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True),
        ),
    ]
