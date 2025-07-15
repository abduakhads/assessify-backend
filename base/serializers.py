from base.models import User
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer

# class BaseUserSerializer(serializers.HyperlinkedModelSerializer):
#     role = serializers.ChoiceField(choices=User.Role.choices)

#     class Meta:
#         model = User
#         fields = ["url", "username", "password", "role"]
#         extra_kwargs = {"password": {"write_only": True}}

#     def create(self, validated_data):
#         password = validated_data.pop("password")
#         user = User.objects.create(**validated_data)

#         user.set_password(password)
#         user.save()

#         return user


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Role.choices)

    class Meta(UserCreateSerializer.Meta):
        fields = ['id', 'username', 'email', 'password', 'role']