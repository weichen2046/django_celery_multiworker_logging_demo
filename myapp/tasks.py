from celery import shared_task
import logging

# 配置日志
logger = logging.getLogger(__name__)

@shared_task
def my_task():
    # 每10秒执行的任务内容
    message = "定时任务执行中..."
    logger.info(message)
    print(message)
    return message