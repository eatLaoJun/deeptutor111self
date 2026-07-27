"""专用的调用链追踪 logger。

一个自包含的 INFO 级 logger，其输出不依赖项目的 root logging 级别
（``data/user/settings/main.yaml`` 默认是 WARNING，会把普通的 ``logger.info``
吞掉）。本 tracer 自己挂一份 stdout ``StreamHandler``，因此 ``[TRACE]`` 行
总能在后端运行的终端里看到 —— 无论其余 logging 如何配置都不受影响。

用法::

    from deeptutor.logging.trace import trace
    trace.log("ChatOrchestrator.handle 开始 | session=%s", session_id)

消息会自动加上 ``[TRACE] `` 前缀，便于 grep 过滤。学习完调用链后，可以
删除这些调用，或把级别降到 DEBUG / 提到 WARNING 来关闭输出。
"""

from __future__ import annotations

import logging
import sys

_LOGGER_NAME = "deeptutor.trace"
_PREFIX = "[TRACE] "
_configured = False


def _ensure_handler(logger: logging.Logger) -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
    # 幂等：绝不重复堆叠 handler。
    has_ours = any(
        getattr(h, "_deeptutor_trace_handler", False) for h in logger.handlers
    )
    if not has_ours:
        setattr(handler, "_deeptutor_trace_handler", True)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # 不向 root logger 冒泡（root 的 WARNING 会丢弃它，且其 handler 会重复输出）。
    logger.propagate = False
    _configured = True


class _Tracer:
    """提供 ``.log(fmt, *args)`` 的薄封装，按 INFO 级别输出追踪行。"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(_LOGGER_NAME)
        _ensure_handler(self._logger)

    def log(self, message: str, *args: object) -> None:
        self._logger.info(_PREFIX + message, *args)


trace = _Tracer()

__all__ = ["trace"]
