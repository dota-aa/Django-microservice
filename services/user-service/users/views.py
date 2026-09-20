from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserRegisterSerializer, CustomTokenObtainPairSerializer, UserSerializer


# ========================================================
# Service Health check
# ========================================================
class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'service': 'user-service', 'status': 'ok'})


# ========================================================
# Auth
# ========================================================
class UserRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegisterSerializer


class UserLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
