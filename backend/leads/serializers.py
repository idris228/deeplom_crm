from rest_framework import serializers
from users.models import User
from .models import Lead, LeadHistory


class LeadSerializer(serializers.ModelSerializer):
    responsible_id = serializers.PrimaryKeyRelatedField(
        source='responsible',
        queryset=User.objects.all(),
    )

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'email', 'source',
            'status', 'budget', 'comment', 'responsible_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeadHistorySerializer(serializers.ModelSerializer):
    changed_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeadHistory
        fields = ['id', 'action', 'old_value', 'new_value', 'changed_by_id', 'created_at']


class LeadConvertResponseSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    deal_id = serializers.IntegerField()
    status = serializers.CharField()