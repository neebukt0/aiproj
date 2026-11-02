from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    CLIENT = 'client', 'Клиент'
    EMPLOYEE = 'employee', 'Сотрудник'
    ADMIN = 'admin', 'Администратор'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role=Role.CLIENT):
        if not email:
            raise ValueError('Email обязателен')
        user = self.model(email=email, role=role)
        user.set_password(password or 'changeme123!')
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, role=Role.ADMIN):
        return self.create_user(email=email, password=password, role=role)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
