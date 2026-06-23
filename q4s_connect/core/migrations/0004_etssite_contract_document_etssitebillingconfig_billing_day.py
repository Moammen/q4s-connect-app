from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_delete_etssitereading'),
    ]

    operations = [
        migrations.AddField(
            model_name='etssite',
            name='contract_document',
            field=models.FileField(blank=True, null=True, upload_to='billing_contracts/'),
        ),
        migrations.AddField(
            model_name='etssitebillingconfig',
            name='billing_day',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                choices=[(d, d) for d in range(1, 29)],
                help_text='Day of the month billing cycle starts (1–28)',
            ),
        ),
    ]
