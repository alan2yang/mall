import re

from django_redis import get_redis_connection
from rest_framework import serializers

from .models import User


class CreateUserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True,label='确认密码')
    sms_code = serializers.CharField(write_only=True, label='短信验证码')
    allow = serializers.CharField(write_only=True, label='同意协议')

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow')
        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def validate_allow(self, value):
        """检验用户是否同意协议"""
        if value != 'true':
            raise serializers.ValidationError('请同意用户协议')
        return value

    def validate(self, attr):

        if attr['password'] != attr['password2']:
            raise serializers.ValidationError('两次密码不一致')

        redis_conn = get_redis_connection('verify_codes')
        mobile = attr['mobile']
        real_sms_code = redis_conn.get('sms_%s' % mobile)
        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')
        if attr['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('短信验证码错误')

        return attr

    def create(self, validated_data):

        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        user=User.objects.create(**validated_data)

        user.set_password(validated_data['password'])

        user.save()

        return user