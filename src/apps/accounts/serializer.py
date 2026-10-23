from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate

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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required = True)
    password = serializers.CharField(min_length = 8,required = True)
    def validate(self, attrs):
        if not attrs['email']:
            raise serializers.ValidationError('email is required')
        user = authenticate(email= attrs['email'],password= attrs['password'])
        if not user:
            raise serializers.ValidationError('Please enter a valid email & password')
        attrs['user'] =user
        return attrs


