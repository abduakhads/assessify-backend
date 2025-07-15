from django.shortcuts import render

from base.models import User
from rest_framework import permissions, viewsets


# from base.serializers import BaseUserSerializer

# class UserViewSet(viewsets.ModelViewSet):
#     queryset = User.objects.all().order_by("-date_joined")
#     serializer_class = BaseUserSerializer
#     permission_classes = [permissions.IsAuthenticated]
