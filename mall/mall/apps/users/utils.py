import re

from django.contrib.auth.backends import ModelBackend

from .models import User


def jwt_response_payload_handler(token, user=None, request=None):
    return {
        'id': user.id,
        'username': user.username,
        'token': token
    }


def get_user(account):
    try:
        if re.match('^1[3-9]\d{9}$', account):

            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):

    def authentication(self, request, username=None, password=None, **kwargs):
        user = get_user(username)

        if user is not None and user.check_password(password):
            return user
