# utils/time_aware.py
"""时间感知模块"""

from datetime import datetime
from typing import Tuple


class TimeAware:
    """时间感知"""

    @staticmethod
    def get_style() -> Tuple[str, str]:
        """根据时间返回回复风格"""
        hour = datetime.now().hour
        if hour >= 23 or hour <= 5:
            return "简短", "【夜間】簡潔な返信"
        elif hour >= 19:
            return "适度精简", "【夕方】やや簡潔な返信"
        return "详细", "【昼間】詳細な返信"