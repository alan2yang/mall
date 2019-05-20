from django.shortcuts import render
from rest_framework.generics import CreateAPIView

from . import serializers

# Create your views here.


# post /users/
class UserView(CreateAPIView):

    serializer_class = serializers.CreateUserSerializer
