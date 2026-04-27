from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        MANAGER = 'MANAGER', 'Менеджер'
        EMPLOYEE = 'EMPLOYEE', 'Сотрудник'
        CLIENT = 'CLIENT', 'Клиент'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        verbose_name='Роль'
    )

    company = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Название компании'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )

    position = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Должность'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT


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
        User,
        on_delete=models.PROTECT,
        related_name='leads',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company_id', 'status']),
            models.Index(fields=['company_id', 'responsible']),
        ]


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
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, blank=True, null=True, related_name='deals')
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=10, default='RUB')
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.NEW, db_index=True)
    close_reason = models.TextField(blank=True, null=True)
    responsible = models.ForeignKey(
        User,
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
        indexes = [
            models.Index(fields=['company_id', 'stage']),
            models.Index(fields=['company_id', 'responsible']),
            models.Index(fields=['company_id', 'created_at']),
        ]


class LeadHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='history_entries')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=120)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class DealHistory(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='history_entries')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(max_length=120)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
