from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_etssitebillingconfig_delta_t_fee_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='etssitebilling',
            name='billing_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
