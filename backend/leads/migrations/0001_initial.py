# Generated manually to bind existing users_* tables to leads app state.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('users', '0003_remove_user_company_id_user_company'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Lead',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, serialize=False)),
                        ('company_id', models.PositiveIntegerField(db_index=True)),
                        ('first_name', models.CharField(max_length=120)),
                        ('last_name', models.CharField(max_length=120)),
                        ('phone', models.CharField(max_length=30)),
                        ('email', models.EmailField(blank=True, max_length=254, null=True)),
                        ('source', models.CharField(max_length=120)),
                        ('status', models.CharField(choices=[('new', 'New'), ('in_progress', 'In Progress'), ('qualified', 'Qualified'), ('converted', 'Converted'), ('closed_lost', 'Closed Lost')], db_index=True, default='new', max_length=30)),
                        ('budget', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                        ('comment', models.TextField(blank=True, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('responsible', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='leads', to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'users_lead',
                    },
                ),
                migrations.CreateModel(
                    name='LeadHistory',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('action', models.CharField(max_length=120)),
                        ('old_value', models.JSONField(blank=True, null=True)),
                        ('new_value', models.JSONField(blank=True, null=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                        ('lead', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history_entries', to='leads.lead')),
                    ],
                    options={
                        'ordering': ['-created_at'],
                        'db_table': 'users_leadhistory',
                    },
                ),
                migrations.AddIndex(
                    model_name='lead',
                    index=models.Index(fields=['company_id', 'status'], name='users_lead_company_2820d1_idx'),
                ),
                migrations.AddIndex(
                    model_name='lead',
                    index=models.Index(fields=['company_id', 'responsible'], name='users_lead_company_394c60_idx'),
                ),
            ],
            database_operations=[],
        ),
    ]
