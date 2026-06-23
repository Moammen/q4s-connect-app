from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_etssite_is_deleted_etssitebilling_is_deleted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='etssitebillingconfig',
            name='delta_t_reference',
        ),
    ]
