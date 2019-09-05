from django.core.mail import send_mail
from django.conf import settings
from celery import Celery
import time

# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

# 创建一个celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.206.128:6379/8')

# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    subject = '新百顺激活信息'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s,欢迎加入新百顺</h1><br/>请点击下面的链接激活账户<a href="http:127.0.0.1:8080/user/active/%s">http:127.0.0.1:8080/user/active/%s</a>' % (
        username, token, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)
    # time.sleep(5)