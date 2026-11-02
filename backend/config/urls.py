from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from users import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', views.RegisterView.as_view(), name='register'),
    path('api/auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/auth/me/', views.MeView.as_view(), name='me'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/resources/', include('resources.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/reports/', include('bookings.reports_urls')),
]
