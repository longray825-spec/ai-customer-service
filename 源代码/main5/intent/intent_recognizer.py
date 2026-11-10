# intent/intent_recognizer.py
"""模糊意图识别模块"""

from collections import defaultdict
from typing import Dict, List
from config import Config
from models import IntentResult


class FuzzyIntentRecognizer:
    """模糊意图识别"""

    def __init__(self):
        self.intent_keywords = Config.INTENT_CATEGORIES
        self.semantic_model = None
        self._init_semantic_model()

    def _init_semantic_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            print(f"⚠️ 语义模型加载失败: {e}")
            self.semantic_model = None

    def recognize(self, text: str) -> IntentResult:
        """识别用户意图"""
        text_lower = text.lower()

        # 关键词匹配
        scores = defaultdict(float)
        keywords_found = []

        for intent, keywords in self.intent_keywords.items():
            for kw in keywords:
                if kw in text or kw.lower() in text_lower:
                    scores[intent] += 1.0
                    keywords_found.append(kw)

        # 归一化分数
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            for intent in scores:
                scores[intent] /= max_score

        # 获取主要意图
        if scores:
            primary_intent = max(scores.items(), key=lambda x: x[1])
            return IntentResult(
                primary_intent=primary_intent[0],
                confidence=min(primary_intent[1], 0.95),
                alternative_intents=[(k, v) for k, v in scores.items() if k != primary_intent[0]][:3],
                keywords_found=list(set(keywords_found))
            )

        # 默认意图
        return IntentResult(
            primary_intent='inquiry',
            confidence=0.3,
            alternative_intents=[],
            keywords_found=[]
        )

    def calculate_intent_similarity(self, intent1: str, intent2: str) -> float:
        """计算意图相似度"""
        if intent1 == intent2:
            return 1.0

        intent_map = {
            'bug_report': ['不具合', 'bug'],
            'payment_issue': ['課金', '支払い'],
            'account_issue': ['アカウント', 'ログイン'],
        }

        for group, members in intent_map.items():
            if intent1 in members and intent2 in members:
                return 0.8

        return 0.0