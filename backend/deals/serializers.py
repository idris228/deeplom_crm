from rest_framework import serializers

from .models import Deal, DealHistory
from leads.models import Lead
from users.models import User


class DealSerializer(serializers.ModelSerializer):
    responsible_id = serializers.PrimaryKeyRelatedField(
        source='responsible',
        queryset=User.objects.all(),
    )
    lead_id = serializers.PrimaryKeyRelatedField(
        source='lead',
        queryset=Lead.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Deal
        fields = [
            'id', 'title', 'client_id', 'lead_id', 'amount', 'currency',
            'stage', 'close_reason', 'responsible_id', 'expected_close_date',
            'created_at', 'updated_at', 'closed_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'closed_at']

    def validate(self, attrs):
        stage = attrs.get('stage', getattr(self.instance, 'stage', Deal.Stage.NEW))
        close_reason = attrs.get('close_reason', getattr(self.instance, 'close_reason', None))
        if stage == Deal.Stage.LOST and not close_reason:
            raise serializers.ValidationError({'close_reason': 'Поле обязательно при закрытии сделки как lost.'})
        return attrs


class DealHistorySerializer(serializers.ModelSerializer):
    changed_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DealHistory
        fields = ['id', 'action', 'old_value', 'new_value', 'changed_by_id', 'created_at']


class DealStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Deal.Stage.choices)


class DealCloseLostSerializer(serializers.Serializer):
    close_reason = serializers.CharField()
