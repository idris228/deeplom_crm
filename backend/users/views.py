from django.contrib.auth import authenticate
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    RegisterSerializer,
)


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
        summary="Регистрация администратора компании",
        description=(
                "Создание нового пользователя с ролью администратора. "
                "Обязательные поля: username, password, password2. "
                "Остальные поля необязательные."
        ),
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                "Пример",
                value={
                    "company": "МедКлиника",
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "phone": "+79999999999",
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


