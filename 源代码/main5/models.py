# models.py
"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class TaskLogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class MemoryLevel(Enum):
    WORKING = "working"
    SHORT_TERM = "short"
    MID_TERM = "mid"
    LONG_TERM = "long"


class ModelType(Enum):
    FAST = "fast"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class TaskLog:
    """任务日志数据模型"""
    task_id: str
    session_id: str
    intent: str
    confidence: float
    response_time_ms: float
    model_used: str
    cache_hit: bool
    human_transfer: bool
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict = field(default_factory=dict)


@dataclass
class MemoryItem:
    """记忆项数据模型"""
    content: str
    embedding: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5
    access_count: int = 0


@dataclass
class IntentResult:
    """意图识别结果"""
    primary_intent: str
    confidence: float
    alternative_intents: List[tuple] = field(default_factory=list)
    keywords_found: List[str] = field(default_factory=list)


@dataclass
class ReplyResult:
    """回复结果"""
    answer: str
    metadata: Dict
    offer_human: bool