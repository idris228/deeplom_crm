from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Lead, Deal, LeadHistory, DealHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'position', 'avatar',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'phone', 'position'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'phone', 'position', 'avatar'
        ]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Подтверждение пароля'
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password2': 'Пароли не совпадают'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        if 'role' not in validated_data and hasattr(User, 'Role') and hasattr(User.Role, 'EMPLOYEE'):
            validated_data['role'] = User.Role.ADMIN

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


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


class LeadHistorySerializer(serializers.ModelSerializer):
    changed_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeadHistory
        fields = ['id', 'action', 'old_value', 'new_value', 'changed_by_id', 'created_at']


class DealHistorySerializer(serializers.ModelSerializer):
    changed_by_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DealHistory
        fields = ['id', 'action', 'old_value', 'new_value', 'changed_by_id', 'created_at']


class LeadConvertResponseSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    deal_id = serializers.IntegerField()
    status = serializers.CharField()


class DealStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Deal.Stage.choices)


class DealCloseLostSerializer(serializers.Serializer):
    close_reason = serializers.CharField()
