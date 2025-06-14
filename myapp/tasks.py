from celery import shared_task
import logging
import os
import threading

# 配置日志
logger = logging.getLogger(__name__)

@shared_task
def my_task():
    # 每10秒执行的任务内容
    message = f"定时任务执行中... [PID: {os.getpid()}, TID: {threading.get_ident()}]"
    logger.info(message)
    return message