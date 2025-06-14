import re
from logging.handlers import TimedRotatingFileHandler

class MinuteRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, **kwargs):
        # 配置每分钟轮换一次日志文件
        super().__init__(**kwargs)
        # 设置日志文件名后缀格式为YYYYMMDDHHMM
        self.suffix = "%Y%m%d%H%M"
        # 设置匹配后缀的正则表达式
        self.extMatch = re.compile(r'^\d{12}$')