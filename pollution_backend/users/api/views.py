from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from pollution_backend.users.models import ApiKey
from ..api.serializers import ApiKeySerializer
from pollution_backend.users.models import Institution
from .serializers import UserSerializer, InstitutionSerializer
from django.utils import timezone
from datetime import timedelta
from pollution_backend.users.api.permissions import IsAdvancedUser

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class InstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [AllowAny]


class ApiKeyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdvancedUser]
    serializer_class = ApiKeySerializer
    pagination_class = None

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        api_key = self.get_object()
        api_key.refresh()
        return Response({'status': 'Key refreshed', 'expires_at': api_key.expires_at})
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save()
        return Response({'status': 'Key revoked'})

    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        api_key = self.get_object()
        api_key.expires_at = timezone.now() - timedelta(seconds=1)
        api_key.save()
        return Response({'status': 'Key expired'})