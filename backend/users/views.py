from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from users.models import User
from users.serializers import RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token обязателен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {'detail': 'Successfully logged out'},
            status=status.HTTP_205_RESET_CONTENT,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
