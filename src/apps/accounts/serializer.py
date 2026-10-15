from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'role'
        ]
        extra_kwargs = {
            "password":{
                "write_only" : True,
                "min_length":8
            }
        }
    def validate(self, attrs):
        if not attrs['email']:
            raise serializers.ValidationError('email is required')
        if len(attrs['password']) < 8:
            raise serializers.ValidationError('password must be 8 charactor')
        return attrs

    def create(self, validated_data):
        if validated_data['role']  == User.RoleChoices.BOSS:
            return User.objects.create_superuser(**validated_data)
        return User.objects.create_user(**validated_data)