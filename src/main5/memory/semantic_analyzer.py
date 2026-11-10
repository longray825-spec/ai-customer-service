# memory/semantic_analyzer.py
"""语义分析模块"""

from config import Config


class SemanticAnalyzer:
    """语义分析：用于检测重复问题和关键词"""

    def __init__(self):
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        except Exception as e:
            print(f"⚠️ 语义分析模型加载失败: {e}")
            self.model = None

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算语义相似度"""
        if self.model is None or not text1 or not text2:
            return 0.0
        try:
            emb1 = self.model.encode([text1[:500]])
            emb2 = self.model.encode([text2[:500]])
            from numpy.linalg import norm
            return float((emb1 @ emb2.T)[0][0] / (norm(emb1) * norm(emb2)))
        except:
            return 0.0

    def contains_helpless_keywords(self, text: str) -> bool:
        """检测无助关键词"""
        for keyword in Config.HELPLESS_KEYWORDS:
            if keyword in text:
                return True
        return False

    def extract_core_meaning(self, text: str) -> str:
        """提取核心含义"""
        remove_words = [
            "教えて", "ください", "お願い", "助けて", "どうすれば",
            "请问", "帮忙", "谢谢", "求助", "怎么办"
        ]
        result = text
        for word in remove_words:
            result = result.replace(word, "")
        return result.strip()[:100]