# config.py
"""配置模块 - 集中管理所有配置"""

import os
from typing import Dict, List


class Config:
    # API配置 - 确保正确读取
    DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("dashscope_api_key") or ""
    MODEL_NAME = "qwen3.5-plus"
    FAST_MODEL = "qwen-plus"
    EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    # 添加初始化打印
    @classmethod
    def check_config(cls):
        print(f"🔑 API Key 配置状态: {'已配置' if cls.DASHSCOPE_API_KEY else '未配置'}")
        print(f"📝 主模型: {cls.MODEL_NAME}")
        print(f"⚡ 快速模型: {cls.FAST_MODEL}")

    # 记忆配置
    SHORT_TERM_MEMORY_SIZE = 100
    MID_TERM_MEMORY_SIZE = 50
    TOP_K_RETRIEVAL = 3

    # 缓存配置
    CACHE_TTL = 3600
    CACHE_MAX_SIZE = 1000

    # 异步配置
    ASYNC_TIMEOUT = 3.0

    # 转人工策略
    CONFIDENCE_THRESHOLD = 0.5
    SIMILARITY_THRESHOLD = 0.75
    MAX_REPEAT_COUNT = 3
    MAX_USELESS_FEEDBACK = 3
    MAX_HELPLESS_KEYWORDS = 3

    # 无助关键词
    HELPLESS_KEYWORDS: List[str] = [
        "まだダメ", "まだ無理", "解決しない", "できない",
        "うまくいかない", "効果がない", "変わらない",
        "还是不行", "没用", "没解决", "不好使", "无效",
        "だめだった", "無理だった", "動かない", "エラーまま",
        "試した", "やったけど", "だめ", "ダメ", "無理"
    ]

    # 意图分类
    INTENT_CATEGORIES: Dict[str, List[str]] = {
        'bug_report': ['フリーズ', 'クラッシュ', 'エラー', 'バグ', '動かない', '不具合', '闪退', '崩溃', 'bug'],
        'payment_issue': ['課金', '購入', 'アイテム', '届かない', 'ジェム', '充值', '购买', '未到账'],
        'account_issue': ['アカウント', 'ログイン', 'パスワード', '登录', '密码', '账号'],
        'gameplay_question': ['攻略', 'イベント', 'ガチャ', 'レベル', '攻略', '活动', '抽卡', '等级'],
        'inquiry': ['問い合わせ', '連絡', 'お問い合わせ', '咨询', '联系'],
        'feedback': ['意見', '要望', '提案', '意见', '建议']
    }

    DEVICE_CATEGORIES: Dict[str, List[str]] = {
        'iOS': ['iPhone', 'iPad', 'iOS'],
        'Android': ['Android', 'Xperia', 'Galaxy', 'Pixel'],
        'PC': ['Windows', 'Mac', 'PC']
    }

    INQUIRY_TYPE_MAP: Dict[str, str] = {
        '不具合': '不具合について',
        'アカウント': 'アカウントについて',
        '課金': '課金について',
        '問い合わせ': 'お問い合わせ',
        '意見・要望': '意見・要望'
    }