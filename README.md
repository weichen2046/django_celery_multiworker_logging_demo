# Django Celery 多Worker日志管理Demo

## 项目概述
本项目是一个演示工程，展示在Celery多Worker进程环境下，如何将日志安全地输出到单个轮转日志文件中，避免多进程写入冲突和日志文件异常。

## 核心问题
当Celery启动多个Worker进程时，传统的文件日志处理器会导致：
- 日志文件内容错乱（多进程同时写入）
- 日志轮转异常（多个进程尝试同时轮转文件）
- 重复日志或丢失日志条目

## 解决方案
本项目通过以下技术实现安全的多进程日志管理：

### 1. 队列化日志处理
使用`MyQueueListener`和`QueueHandler`将日志事件通过线程安全的队列传递给单个日志写入进程。

其中`MyQueueListener`添加了`force_return`方法，用于在Worker进程主动退出时，强制返回队列哨兵值，以使`QueueListener`线程退出。

### 2. 进程隔离
通过Celery信号机制确保日志监听器仅在主进程启动，Worker子进程自动停止继承的监听器实例

```python
# myapp/apps.py
from celery.signals import worker_process_init

def stop_listener_on_worker_init(**kwargs):
    try:
        app_config = apps.get_app_config('myapp')
        if hasattr(app_config, 'listener') and app_config.listener:
            # Do not use listener.stop() to avoid multiprocessing.Queue() exit.
            app_config.listener.force_return()
            app_config.listener = None
    except Exception as e:
        logger.error(f"Failed to stop listener in worker process: {e}")
```

### 3. 线程安全控制
对共享变量访问添加线程锁，防止并发修改导致的状态不一致

### 4. 定时日志轮转
实现`MinuteRotatingFileHandler`按分钟轮转日志文件，保留指定数量的备份

```python
# myapp/apps.py
file_handler = MinuteRotatingFileHandler(
    filename=str(log_dir / 'celery.log'),
    when='M',
    interval=1,
    backupCount=5,
    encoding='utf-8'
)
```

## 项目结构
```
├── myapp/
│   ├── apps.py        # 应用配置和日志监听器设置
│   └── tasks.py       # Celery任务示例
└── myproject/
    ├── celery.py      # Celery配置
    ├── settings.py    # Django配置，包含日志设置
    └── logging_handlers.py  # 自定义日志处理器
```

## 关键配置

### 日志配置 (settings.py)
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} [PID:{process}, TID:{thread}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Celery配置 (celery.py)
```python
# 禁用Celery日志劫持
app.conf.worker_hijack_root_logger = False
```

## 使用方法

### 安装依赖
```bash
pipenv install
```

### 启动Celery Worker
```bash
pipenv run celery -A myproject worker --loglevel=info --concurrency=4
```

### 触发测试任务
```bash
pipenv run python manage.py shell
>>> from myapp.tasks import my_task
>>> my_task.delay()
```

## 日志文件
日志文件位于`logs/celery.log`，并会按分钟自动轮转，格式如下：
```
INFO 2023-11-15 10:30:00 tasks [PID:1234, TID:5678] 定时任务执行中...
```

## 总结
本项目通过队列化日志处理、进程隔离和线程安全控制，解决了Celery多Worker环境下的日志管理问题，确保日志文件完整性和正确性。