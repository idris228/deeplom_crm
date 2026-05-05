from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal, DealHistory
from users.models import User
from .models import Lead, LeadHistory
from .serializers import LeadConvertResponseSerializer, LeadHistorySerializer, LeadSerializer


def _is_admin(user):
    return user.role == User.Role.ADMIN


def _is_manager(user):
    return user.role == User.Role.MANAGER


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
        summary='Список лидов',
        parameters=[
            OpenApiParameter(name='search', type=str),
            OpenApiParameter(name='status', type=str),
            OpenApiParameter(name='source', type=str),
            OpenApiParameter(name='responsible_id', type=int),
            OpenApiParameter(name='created_from', type=str),
            OpenApiParameter(name='created_to', type=str),
            OpenApiParameter(name='ordering', type=str),
        ],
    ),
    create=extend_schema(summary='Создать лид'),
    retrieve=extend_schema(summary='Карточка лида'),
    partial_update=extend_schema(summary='Обновить лид'),
    destroy=extend_schema(summary='Удалить лид'),
)
class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = getattr(self.request.user, 'company_id', None)
        if company_id is None:
            return Lead.objects.none()
        qs = Lead.objects.filter(company_id=company_id).select_related('responsible')
        user = self.request.user
        if _is_employee(user):
            qs = qs.filter(responsible=user)

        qp = self.request.query_params
        search = qp.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        if qp.get('status'):
            qs = qs.filter(status=qp['status'])
        if qp.get('source'):
            qs = qs.filter(source__iexact=qp['source'])
        if qp.get('responsible_id'):
            qs = qs.filter(responsible_id=qp['responsible_id'])

        created_from = _parse_date(qp.get('created_from'), 'created_from')
        created_to = _parse_date(qp.get('created_to'), 'created_to')
        if created_from and created_to and created_from > created_to:
            raise ValidationError({'date_range': 'created_from не может быть больше created_to'})
        if created_from:
            qs = qs.filter(created_at__date__gte=created_from)
        if created_to:
            qs = qs.filter(created_at__date__lte=created_to)

        ordering = qp.get('ordering', '-created_at')
        if ordering.lstrip('-') in {'created_at', 'updated_at', 'status'}:
            qs = qs.order_by(ordering)
        return qs

    def perform_create(self, serializer):
        responsible = serializer.validated_data['responsible']
        if responsible.company_id != self.request.user.company_id:
            raise PermissionDenied('Нельзя назначать ответственного из другой компании.')
        lead = serializer.save(company_id=self.request.user.company_id)
        LeadHistory.objects.create(
            lead=lead,
            changed_by=self.request.user,
            action='created',
            new_value={'status': lead.status},
        )

    def perform_update(self, serializer):
        lead = self.get_object()
        old = {'status': lead.status, 'budget': str(lead.budget) if lead.budget is not None else None}
        responsible = serializer.validated_data.get('responsible')
        if responsible and responsible.company_id != self.request.user.company_id:
            raise PermissionDenied('Нельзя назначать ответственного из другой компании.')
        updated = serializer.save()
        LeadHistory.objects.create(
            lead=updated,
            changed_by=self.request.user,
            action='updated',
            old_value=old,
            new_value={'status': updated.status, 'budget': str(updated.budget) if updated.budget is not None else None},
        )

    def perform_destroy(self, instance):
        if _is_employee(self.request.user):
            raise PermissionDenied('Недостаточно прав для удаления лида.')
        LeadHistory.objects.create(
            lead=instance,
            changed_by=self.request.user,
            action='deleted',
        )
        instance.delete()

    @extend_schema(
        summary='Конвертация лида в сделку',
        responses={200: LeadConvertResponseSerializer, 409: OpenApiResponse(description='Лид уже конвертирован')},
    )
    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        lead = self.get_object()
        if lead.status == Lead.Status.CONVERTED:
            return Response({'detail': 'Лид уже сконвертирован.'}, status=status.HTTP_409_CONFLICT)

        deal = Deal.objects.create(
            company_id=lead.company_id,
            title=f'{lead.first_name} {lead.last_name}'.strip(),
            client_id=lead.id,
            lead=lead,
            amount=lead.budget or 0,
            responsible=lead.responsible,
        )
        old_status = lead.status
        lead.status = Lead.Status.CONVERTED
        lead.save(update_fields=['status', 'updated_at'])

        LeadHistory.objects.create(
            lead=lead,
            changed_by=request.user,
            action='converted',
            old_value={'status': old_status},
            new_value={'status': lead.status, 'deal_id': deal.id},
        )
        DealHistory.objects.create(
            deal=deal,
            changed_by=request.user,
            action='created_from_lead',
            new_value={'lead_id': lead.id},
        )
        return Response({'lead_id': lead.id, 'deal_id': deal.id, 'status': lead.status})

    @extend_schema(summary='История лида', responses={200: LeadHistorySerializer(many=True)})
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadHistorySerializer(lead.history_entries.all(), many=True)
        return Response(serializer.data)




class DashboardScopeMixin:
    def _deals_qs(self, request):
        company_id = getattr(request.user, 'company_id', None)
        if company_id is None:
            return Deal.objects.none()
        qs = Deal.objects.filter(company_id=company_id)
        if _is_employee(request.user):
            qs = qs.filter(responsible=request.user)
        elif _is_manager(request.user):
            qs = qs.filter(responsible=request.user)
        return qs

    def _leads_qs(self, request):
        company_id = getattr(request.user, 'company_id', None)
        if company_id is None:
            return Lead.objects.none()
        qs = Lead.objects.filter(company_id=company_id)
        if _is_employee(request.user):
            qs = qs.filter(responsible=request.user)
        elif _is_manager(request.user):
            qs = qs.filter(responsible=request.user)
        return qs


@extend_schema(
    summary='Dashboard summary',
    responses={
        200: inline_serializer(
            name='DashboardSummary',
            fields={
                'leads_total': serializers.IntegerField(),
                'leads_new': serializers.IntegerField(),
                'deals_active': serializers.IntegerField(),
                'deals_won': serializers.IntegerField(),
                'pipeline_amount': serializers.DecimalField(max_digits=14, decimal_places=2),
                'won_amount': serializers.DecimalField(max_digits=14, decimal_places=2),
                'conversion_rate': serializers.FloatField(),
                'avg_check': serializers.DecimalField(max_digits=14, decimal_places=2),
            },
        ),
    },
)
class DashboardSummaryView(APIView, DashboardScopeMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leads_qs = self._leads_qs(request)
        deals_qs = self._deals_qs(request)
        leads_total = leads_qs.count()
        converted = leads_qs.filter(status=Lead.Status.CONVERTED).count()
        won_qs = deals_qs.filter(stage=Deal.Stage.WON)
        result = {
            'leads_total': leads_total,
            'leads_new': leads_qs.filter(status=Lead.Status.NEW).count(),
            'deals_active': deals_qs.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST]).count(),
            'deals_won': won_qs.count(),
            'pipeline_amount': deals_qs.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST]).aggregate(v=Sum('amount'))['v'] or 0,
            'won_amount': won_qs.aggregate(v=Sum('amount'))['v'] or 0,
            'conversion_rate': round((converted / leads_total) if leads_total else 0, 4),
            'avg_check': won_qs.aggregate(v=Sum('amount'))['v'] / won_qs.count() if won_qs.count() else 0,
        }
        return Response(result)


@extend_schema(summary='Dashboard funnel')
class DashboardFunnelView(APIView, DashboardScopeMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        lead_stage_counts = self._leads_qs(request).values('status').annotate(count=Count('id'))
        deal_stage_counts = self._deals_qs(request).values('stage').annotate(count=Count('id'))
        stages = []
        for row in lead_stage_counts:
            stages.append({'key': row['status'], 'count': row['count']})
        for row in deal_stage_counts:
            if row['stage'] in {Deal.Stage.WON, Deal.Stage.LOST}:
                stages.append({'key': row['stage'], 'count': row['count']})
        return Response({'stages': stages})


@extend_schema(summary='Dashboard revenue')
class DashboardRevenueView(APIView, DashboardScopeMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        deals = self._deals_qs(request).filter(stage=Deal.Stage.WON)
        return Response({'won_amount': deals.aggregate(v=Sum('amount'))['v'] or 0})


@extend_schema(summary='Dashboard manager performance')
class DashboardManagerPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        company_id = getattr(request.user, 'company_id', None)
        if company_id is None:
            return Response([])
        deals = Deal.objects.filter(company_id=company_id)
        if not _is_admin(request.user):
            deals = deals.filter(responsible=request.user)
        data = (
            deals.values('responsible_id')
            .annotate(total=Count('id'), won=Count('id', filter=Q(stage=Deal.Stage.WON)), amount=Sum('amount'))
            .order_by('-amount')
        )
        return Response(list(data))
