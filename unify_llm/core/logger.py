import os
import sys
import logging
from pathlib import Path

import rootutils

ROOT_DIR = rootutils.setup_root(search_from=os.getcwd(), indicator=['.project-root'], pythonpath=True)


class UTF8StreamHandler(logging.StreamHandler):
    """
    自定义 StreamHandler，在 Windows 上强制使用 UTF-8 编码
    处理 GBK 编码问题，同时避免文件关闭问题
    """

    def emit(self, record):
        """覆盖 emit 方法以处理 UTF-8 编码"""
        try:
            msg = self.format(record)
            stream = self.stream

            # 检查 stream 是否已关闭
            if hasattr(stream, 'closed') and stream.closed:
                return

            # 在 Windows 上，尝试用 UTF-8 编码写入，失败时用 replace 错误处理
            if sys.platform == 'win32':
                try:
                    # 首先尝试直接写入（如果 stream 已经是 UTF-8）
                    stream.write(msg + self.terminator)
                    self.flush()
                except UnicodeEncodeError:
                    # 如果编码失败，尝试用 UTF-8 编码后写入
                    if hasattr(stream, 'buffer'):
                        # stream 是文本流，有 buffer
                        encoded = (msg + self.terminator).encode('utf-8', errors='replace')
                        stream.buffer.write(encoded)
                        stream.buffer.flush()
                    else:
                        # stream 是二进制流或其他
                        encoded = (msg + self.terminator).encode('utf-8', errors='replace')
                        stream.write(encoded)
                        self.flush()
            else:
                # 非 Windows 系统直接写入
                stream.write(msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)


def setup_logger(name: str = __name__) -> logging.Logger:
    """设置日志记录器"""

    # 延迟导入以避免循环依赖
    from unify_llm.core.config import settings

    # 创建日志目录
    log_file_path = ROOT_DIR / settings.LOG_FILE
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    file_handler.setFormatter(formatter)

    # 控制台处理器（使用自定义的 UTF8StreamHandler）
    console_handler = UTF8StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建默认日志记录器
logger = setup_logger("CRFGeneration")

# 导出以供外部使用
__all__ = ['logger', 'setup_logger', 'UTF8StreamHandler']
