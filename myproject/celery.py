import os
from celery import Celery

# 设置默认的Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')

# 使用Django的设置文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有Django应用中的任务
app.autodiscover_tasks()