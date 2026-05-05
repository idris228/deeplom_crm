from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('deals', '0001_initial'),
        ('leads', '0001_initial'),
        ('users', '0003_remove_user_company_id_user_company'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='DealHistory'),
                migrations.DeleteModel(name='Deal'),
                migrations.DeleteModel(name='LeadHistory'),
                migrations.DeleteModel(name='Lead'),
            ],
            database_operations=[],
        ),
    ]
