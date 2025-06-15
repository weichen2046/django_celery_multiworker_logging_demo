from django.apps import AppConfig
import logging
import threading
from logging.handlers import QueueListener
from myproject.logging_handlers import MinuteRotatingFileHandler
from django.conf import settings
from pathlib import Path
from celery.signals import worker_process_init
from django.apps import apps

logger = logging.getLogger(__name__)

class MyQueueListener(QueueListener):
    def __init__(self, queue, *handlers, respect_handler_level: bool = False):
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self._forced_return = False
        self.lock = threading.Lock()

    def _force_return(self):
        logger.info('called force return')
        with self.lock:
            self._forced_return = True

    def dequeue(self, block: bool):
        '''
        从队列中获取日志记录。
        如果已设置强制返回标志，此方法会立即返回哨兵值。
        否则，它会调用父类的 dequeue 方法来获取记录。
        '''
        with self.lock:
            if self._forced_return:
                logger.info('return sentinel')
                return QueueListener._sentinel
        print('return super.dequeue(True)')
        return super().dequeue(block)

    def stop(self):
        '''
        停止队列监听器。
        此方法会调用 _force_return 方法来设置强制返回标志，
        并关闭所有关联的处理器（如果它们有 close 方法），
        最后等待线程结束。
        '''
        self._force_return()
        for handler in self.handlers:
            if hasattr(handler, 'close'):
                logger.info('call close() on handler')
                handler.close()
        self._thread.join()
        self._thread = None
        logger.info('call stop() on QueueListener done')

def stop_listener_on_worker_init(**kwargs):
    try:
        logger.info('stop_listener_on_worker_init')
        app_config = apps.get_app_config('myapp')
        if hasattr(app_config, 'listener') and app_config.listener:
            logger.info('stop listener in worker process now')
            app_config.listener.stop()
            app_config.listener = None
    except Exception as e:
        logger.error(f"Failed to stop listener in worker process: {e}")

class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        # 确保日志目录存在
        log_dir = Path(settings.BASE_DIR) / 'logs'
        log_dir.mkdir(exist_ok=True)

        # 创建文件处理器
        file_handler = MinuteRotatingFileHandler(
            filename=str(log_dir / 'celery.log'),
            when='M',
            interval=1,
            backupCount=5,
            encoding='utf-8'
        )

        # 设置日志格式
        formatter = logging.Formatter(
            '{levelname} {asctime} {module} [PID:{process}, TID:{thread}] {message}',
            style='{'
        )
        file_handler.setFormatter(formatter)
        print('QueueListener started successfully')
        logger.info('QueueListener started successfully')

        worker_process_init.connect(stop_listener_on_worker_init)

        # 创建并启动队列监听器
        self.listener = MyQueueListener(settings.LOG_QUEUE, file_handler)
        self.listener.start()
