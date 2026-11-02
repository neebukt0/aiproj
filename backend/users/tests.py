from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Role, User


class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='client@example.com',
            password='secret12345',
            role=Role.CLIENT,
        )

    def test_register_creates_user_with_client_role(self):
        response = self.client.post(
            reverse('register'),
            {'email': 'new@example.com', 'password': 'secret12345', 'role': 'client'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'new@example.com')
        self.assertEqual(response.data['role'], 'client')

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'client@example.com', 'password': 'secret12345'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_returns_new_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(
            reverse('logout'),
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        self.assertTrue(BlacklistedToken.objects.filter(
            token__jti=str(refresh['jti']),
        ).exists())

    def test_me_returns_current_user(self):
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(access)}')
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'client@example.com')
        self.assertEqual(response.data['role'], 'client')

    def test_me_requires_authentication(self):
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
