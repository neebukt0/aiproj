from rest_framework import serializers

from users.models import Role, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'role')
        read_only_fields = ('id', 'email', 'role')

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role') or Role.CLIENT,
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'role', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'email', 'role', 'is_active', 'created_at', 'updated_at')
