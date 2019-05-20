import random

import logging
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from django_redis import get_redis_connection
from django.http import HttpResponse

from mall.libs.captcha.captcha import captcha

from users.models import User
from . import constants
from . import serializers
from mall.utils.yuntongxun.sms import CCP
from celery_tasks.sms.tasks import send_sms_code

# Create your views here.

logger=logging.getLogger('django')


# get /usernames/(?P<username>\w{5,20})/count/
class UsernameCountView(APIView):

    def get(self,request,username):
        count=User.objects.filter(username=username).count()

        data={
            'username':username,
            'count':count
        }
        return Response(data)


# get /mobiles/(?P<mobile>1[3-9]\d{9})/count
class MobileCountView(APIView):
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }
        return Response(data)


# get /image_codes/(?P<image_code_id>[\w-]+)
class ImageCodeView(APIView):

    def get(self,request,image_code_id):

        # 生成图片验证码
        text,image=captcha.generate_captcha()
        # 保存验证码值
        redis_conn=get_redis_connection('verify_codes')
        redis_conn.setex('image_{}'.format(image_code_id),constants.IMAGE_CODE_REDIS_EXPIRES,text)

        # 返回图片
        return HttpResponse(image,content_type='image/jpg')


# get /sms_codes/(?P<mobile>1[3-9]\d{9})/?image_code_id=xxx&text=xxx
class SMSCodeView(GenericAPIView):

    serializer_class = serializers.ImageCodeCheckSerializer

    def get(self,request,mobile):

        # 通过序列化器进行参数校验
        serializer=self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 生成短信验证码，并保存;同时记录手机号操作情况
        sms_code='{:0<6d}'.format(random.randint(0,999999))

        redis_conn=get_redis_connection('verify_codes')

        # redis_conn.setex('sms_{}'.format(mobile),constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        # redis_conn.setex('send_flag_{}'.format(mobile),constants.SEND_SMS_CODE_INTERVAL,1)

        # 减少与数据库的通信次数
        redis_pipe=redis_conn.pipeline()
        redis_pipe.setex('sms_{}'.format(mobile),constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        redis_pipe.setex('send_flag_{}'.format(mobile),constants.SEND_SMS_CODE_INTERVAL,1)
        redis_pipe.execute()

        # 发送短信验证码
        # try:
        #     expires=constants.IMAGE_CODE_REDIS_EXPIRES//60
        #     ccp = CCP()
        #     result=ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)
        # except Exception as e:
        #     logger.error("发送验证码短信[异常][ mobile: {}, message: {} ]".format(mobile, e))
        #     return Response({'message': 'failed'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     if result == 0:
        #         logger.info("发送验证码短信[正常][ mobile: {} ]".format(mobile))
        #         return Response({'message':'OK'})
        #     else:
        #         logger.error("发送验证码短信[异常][ mobile: {}, message: {} ]".format(mobile, e))
        #         return Response({'message': 'failed'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 异步发送短信
        expires = constants.IMAGE_CODE_REDIS_EXPIRES // 60

        send_sms_code.delay(mobile, sms_code, expires,constants.SMS_CODE_TEMP_ID)

        return Response({'message':'OK'})



