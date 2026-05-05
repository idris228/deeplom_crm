from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Deal, DealHistory
from .serializers import DealCloseLostSerializer, DealHistorySerializer, DealSerializer, DealStageSerializer
from users.models import User


def _is_employee(user):
    return user.role == User.Role.EMPLOYEE


def _parse_date(value, field_name):
    if not value:
        return None
    try:
        return timezone.datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ValidationError({field_name: 'Неверный формат даты. Используйте YYYY-MM-DD.'}) from exc


@extend_schema_view(
    list=extend_schema(
        summary='Список сделок',
        parameters=[
            OpenApiParameter(name='search', type=str),
            OpenApiParameter(name='stage', type=str),
            OpenApiParameter(name='responsible_id', type=int),
            OpenApiParameter(name='amount_min', type=float),
            OpenApiParameter(name='amount_max', type=float),
            OpenApiParameter(name='closed_from', type=str),
            OpenApiParameter(name='closed_to', type=str),
            OpenApiParameter(name='is_active', type=bool),
            OpenApiParameter(name='ordering', type=str),
        ],
    ),
    create=extend_schema(summary='Создать сделку'),
    retrieve=extend_schema(summary='Карточка сделки'),
    partial_update=extend_schema(summary='Обновить сделку'),
    destroy=extend_schema(summary='Удалить сделку'),
)
class DealViewSet(viewsets.ModelViewSet):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = getattr(self.request.user, 'company_id', None)
        if company_id is None:
            return Deal.objects.none()
        qs = Deal.objects.filter(company_id=company_id).select_related('responsible', 'lead')
        if _is_employee(self.request.user):
            qs = qs.filter(responsible=self.request.user)

        qp = self.request.query_params
        search = qp.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(client_id__icontains=search))
        if qp.get('stage'):
            qs = qs.filter(stage=qp['stage'])
        if qp.get('responsible_id'):
            qs = qs.filter(responsible_id=qp['responsible_id'])
        if qp.get('amount_min'):
            qs = qs.filter(amount__gte=qp['amount_min'])
        if qp.get('amount_max'):
            qs = qs.filter(amount__lte=qp['amount_max'])

        closed_from = _parse_date(qp.get('closed_from'), 'closed_from')
        closed_to = _parse_date(qp.get('closed_to'), 'closed_to')
        if closed_from and closed_to and closed_from > closed_to:
            raise ValidationError({'date_range': 'closed_from не может быть больше closed_to'})
        if closed_from:
            qs = qs.filter(closed_at__date__gte=closed_from)
        if closed_to:
            qs = qs.filter(closed_at__date__lte=closed_to)

        if qp.get('is_active') in {'true', '1', 'True'}:
            qs = qs.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST])

        ordering = qp.get('ordering', '-created_at')
        if ordering.lstrip('-') in {'created_at', 'updated_at', 'amount', 'stage'}:
            qs = qs.order_by(ordering)
        return qs

    def perform_create(self, serializer):
        responsible = serializer.validated_data['responsible']
        if responsible.company_id != self.request.user.company_id:
            raise PermissionDenied('Нельзя назначать ответственного из другой компании.')
        deal = serializer.save(company_id=self.request.user.company_id)
        DealHistory.objects.create(
            deal=deal,
            changed_by=self.request.user,
            action='created',
            new_value={'stage': deal.stage, 'amount': str(deal.amount)},
        )

    def perform_update(self, serializer):
        deal = self.get_object()
        old = {'stage': deal.stage, 'amount': str(deal.amount)}
        updated = serializer.save()
        DealHistory.objects.create(
            deal=updated,
            changed_by=self.request.user,
            action='updated',
            old_value=old,
            new_value={'stage': updated.stage, 'amount': str(updated.amount)},
        )

    @extend_schema(summary='Сменить этап', request=DealStageSerializer, responses={200: DealSerializer})
    @action(detail=True, methods=['post'], url_path='stage')
    def change_stage(self, request, pk=None):
        deal = self.get_object()
        serializer = DealStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_stage = deal.stage
        deal.stage = serializer.validated_data['stage']
        if deal.stage in {Deal.Stage.WON, Deal.Stage.LOST} and not deal.closed_at:
            deal.closed_at = timezone.now()
        deal.save(update_fields=['stage', 'closed_at', 'updated_at'])
        DealHistory.objects.create(
            deal=deal,
            changed_by=request.user,
            action='stage_changed',
            old_value={'stage': old_stage},
            new_value={'stage': deal.stage},
        )
        return Response(DealSerializer(deal).data)

    @extend_schema(summary='Закрыть как успешно', responses={200: DealSerializer})
    @action(detail=True, methods=['post'], url_path='close-won')
    def close_won(self, request, pk=None):
        deal = self.get_object()
        old_stage = deal.stage
        deal.stage = Deal.Stage.WON
        deal.closed_at = timezone.now()
        deal.save(update_fields=['stage', 'closed_at', 'updated_at'])
        DealHistory.objects.create(
            deal=deal,
            changed_by=request.user,
            action='closed_won',
            old_value={'stage': old_stage},
            new_value={'stage': deal.stage},
        )
        return Response(DealSerializer(deal).data)

    @extend_schema(summary='Закрыть как проиграно', request=DealCloseLostSerializer, responses={200: DealSerializer})
    @action(detail=True, methods=['post'], url_path='close-lost')
    def close_lost(self, request, pk=None):
        deal = self.get_object()
        serializer = DealCloseLostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_stage = deal.stage
        deal.stage = Deal.Stage.LOST
        deal.close_reason = serializer.validated_data['close_reason']
        deal.closed_at = timezone.now()
        deal.save(update_fields=['stage', 'close_reason', 'closed_at', 'updated_at'])
        DealHistory.objects.create(
            deal=deal,
            changed_by=request.user,
            action='closed_lost',
            old_value={'stage': old_stage},
            new_value={'stage': deal.stage, 'close_reason': deal.close_reason},
        )
        return Response(DealSerializer(deal).data)

    @extend_schema(summary='История сделки', responses={200: DealHistorySerializer(many=True)})
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        deal = self.get_object()
        serializer = DealHistorySerializer(deal.history_entries.all(), many=True)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        if _is_employee(self.request.user):
            raise PermissionDenied('Недостаточно прав для удаления сделки.')
        DealHistory.objects.create(
            deal=instance,
            changed_by=self.request.user,
            action='deleted',
        )
        instance.delete()
