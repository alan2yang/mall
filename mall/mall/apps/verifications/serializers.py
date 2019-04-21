from rest_framework import serializers
from django_redis import get_redis_connection


class ImageCodeCheckSerializer(serializers.Serializer):
    image_code_id=serializers.UUIDField()
    text=serializers.CharField(min_length=4,max_length=4)

    def validate(self, attrs):
        image_code_id=attrs['image_code_id']
        text=attrs['text']

        redis_conn=get_redis_connection('verify_codes')
        real_image_code_text=redis_conn.get('image_{}'.format(image_code_id))

        # 删除图片验证码
        redis_conn.delete('image_{}'.format(image_code_id))

        if not real_image_code_text:
            raise serializers.ValidationError('图片验证码无效！')

        real_image_code_text=real_image_code_text.decode()

        if real_image_code_text.lower() !=text.lower():
            raise serializers.ValidationError('图片验证码错误！')

        # 设置判断是否频繁发送
        mobile=self.context['view'].kwargs['mobile']  # 获取视图类中的参数　！！！！！！！！！！！
        send_flag=redis_conn.get('send_flag_{}'.format(mobile))

        if send_flag:
            raise serializers.ValidationError('请求次数过于频繁！')

        return attrs
