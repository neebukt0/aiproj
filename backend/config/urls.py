from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.auth_urls')),
    path('api/resources/', include('resources.urls')),
    path('api/bookings/', include('bookings.urls')),
    path('api/reports/', include('bookings.reports_urls')),
]
