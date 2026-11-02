from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.MeView.as_view(), name='me'),
]
