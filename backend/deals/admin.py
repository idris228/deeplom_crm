from django.contrib import admin

from .models import Deal, DealHistory


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'company_id', 'stage', 'amount', 'responsible', 'created_at')
    list_filter = ('stage', 'currency', 'created_at')
    search_fields = ('title', 'client_id')


@admin.register(DealHistory)
class DealHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'deal', 'action', 'changed_by', 'created_at')
    list_filter = ('action', 'created_at')
