# Generated manually to bind existing users_* tables to deals app state.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('leads', '0001_initial'),
        ('users', '0003_remove_user_company_id_user_company'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Deal',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, serialize=False)),
                        ('company_id', models.PositiveIntegerField(db_index=True)),
                        ('title', models.CharField(max_length=255)),
                        ('client_id', models.PositiveIntegerField()),
                        ('amount', models.DecimalField(db_index=True, decimal_places=2, max_digits=14)),
                        ('currency', models.CharField(default='RUB', max_length=10)),
                        ('stage', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('proposal', 'Proposal'), ('negotiation', 'Negotiation'), ('won', 'Won'), ('lost', 'Lost')], db_index=True, default='new', max_length=30)),
                        ('close_reason', models.TextField(blank=True, null=True)),
                        ('expected_close_date', models.DateField(blank=True, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('closed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                        ('lead', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deals', to='leads.lead')),
                        ('responsible', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='deals', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'users_deal',
                    },
                ),
                migrations.CreateModel(
                    name='DealHistory',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('action', models.CharField(max_length=120)),
                        ('old_value', models.JSONField(blank=True, null=True)),
                        ('new_value', models.JSONField(blank=True, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                        ('deal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history_entries', to='deals.deal')),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'users_dealhistory',
                    },
                ),
                migrations.AddIndex(
                    model_name='deal',
                    index=models.Index(fields=['company_id', 'stage'], name='users_deal_company_037cd3_idx'),
                ),
                migrations.AddIndex(
                    model_name='deal',
                    index=models.Index(fields=['company_id', 'responsible'], name='users_deal_company_58ef11_idx'),
                ),
                migrations.AddIndex(
                    model_name='deal',
                    index=models.Index(fields=['company_id', 'created_at'], name='users_deal_company_0e7d48_idx'),
                ),
            ],
            database_operations=[],
        ),
    ]
