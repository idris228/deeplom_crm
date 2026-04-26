from django.contrib.auth import authenticate
from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Deal, DealHistory, Lead, LeadHistory, User
from .serializers import (
    DealCloseLostSerializer,
    DealHistorySerializer,
    DealSerializer,
    DealStageSerializer,
    LeadConvertResponseSerializer,
    LeadHistorySerializer,
    LeadSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
)


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


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'register':
            return RegisterSerializer
        if self.action == 'login':
            return LoginSerializer
        return LoginSerializer

    @extend_schema(
        summary="Авторизация пользователя",
        description="Вход в систему. Возвращает access и refresh токены.",
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                "Пример",
                value={
                    "username": "user1",
                    "password": "StrongPass123!"
                },
                request_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if user is None:
            return Response(
                {'error': 'Неверный логин или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Аккаунт заблокирован'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


    @extend_schema(
        summary="Регистрация пользователя",
        description="Создание нового пользователя (с подтверждением пароля).",
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                "Пример",
                value={
                    "username": "newuser",
                    "password": "StrongPass123!",
                    "password2": "StrongPass123!"
                },
                request_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


    @extend_schema(
        summary="Выход из системы",
        description="Инвалидация refresh токена (logout).",
        examples=[
            OpenApiExample(
                "Пример",
                value={"refresh": "token_here"},
                request_only=True
            )
        ]
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return Response(
                    {'error': 'Refresh токен обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'message': 'Успешный выход'})
        except Exception:
            return Response(
                {'error': 'Невалидный токен'},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema_view(
    list=extend_schema(
        summary="Список пользователей",
        description="Получить список всех пользователей."
    ),
    retrieve=extend_schema(
        summary="Получить пользователя",
        description="Получить пользователя по ID."
    ),
    create=extend_schema(
        summary="Создать пользователя",
        description="Создание пользователя администратором (без password2)."
    ),
    update=extend_schema(
        summary="Полное обновление пользователя",
        description="Обновление всех полей пользователя (PUT)."
    ),
    partial_update=extend_schema(
        summary="Частичное обновление пользователя",
        description="Обновление отдельных полей (PATCH)."
    ),
    destroy=extend_schema(
        summary="Удалить пользователя",
        description="Удаление пользователя по ID."
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    @extend_schema(
        summary="Текущий пользователь",
        description="Получить данные текущего пользователя по JWT."
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        summary="Фильтр по роли",
        description="Получить пользователей по роли (admin, manager, doctor, client)."
    )
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        role = request.query_params.get('role')

        if not role:
            return Response(
                {"error": "Параметр 'role' обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = self.queryset.filter(role=role)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)


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
        user = self.request.user
        if _is_employee(user):
            qs = qs.filter(responsible=user)

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
