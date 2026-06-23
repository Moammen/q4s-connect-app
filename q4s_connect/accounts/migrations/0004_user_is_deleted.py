from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_user_ets_sites_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
