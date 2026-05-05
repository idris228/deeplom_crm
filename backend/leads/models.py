from django.db import models


# Create your models here.
class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        IN_PROGRESS = 'in_progress', 'In Progress'
        QUALIFIED = 'qualified', 'Qualified'
        CONVERTED = 'converted', 'Converted'
        CLOSED_LOST = 'closed_lost', 'Closed Lost'

    id = models.BigAutoField(primary_key=True)
    company_id = models.PositiveIntegerField(db_index=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    source = models.CharField(max_length=120)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW, db_index=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    responsible = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='leads',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'users_lead'
        indexes = [
            models.Index(fields=['company_id', 'status']),
            models.Index(fields=['company_id', 'responsible']),
        ]


class LeadHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='history_entries')
    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=120)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'users_leadhistory'


