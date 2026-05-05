from django.db import models


class Deal(models.Model):
    class Stage(models.TextChoices):
        NEW = 'new', 'New'
        CONTACTED = 'contacted', 'Contacted'
        PROPOSAL = 'proposal', 'Proposal'
        NEGOTIATION = 'negotiation', 'Negotiation'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'

    id = models.BigAutoField(primary_key=True)
    company_id = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    client_id = models.PositiveIntegerField()
    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, blank=True, null=True, related_name='deals')
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=10, default='RUB')
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.NEW, db_index=True)
    close_reason = models.TextField(blank=True, null=True)
    responsible = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='deals',
        db_index=True,
    )
    expected_close_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'users_deal'
        indexes = [
            models.Index(fields=['company_id', 'stage']),
            models.Index(fields=['company_id', 'responsible']),
            models.Index(fields=['company_id', 'created_at']),
        ]


class DealHistory(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='history_entries')
    changed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=120)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'users_dealhistory'
