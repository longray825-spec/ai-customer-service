# llm/knowledge_base.py
"""知识库检索模块"""

from collections import defaultdict
from typing import List, Dict, Tuple


class KnowledgeBase:
    """知识库检索"""

    def __init__(self):
        self.model = None
        self.indexes = {}
        self.data = {}
        self._init_model()

    def _init_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            from config import Config
            print(f"📦 加载向量模型: {Config.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
            print("✅ 向量模型加载完成")
        except Exception as e:
            print(f"⚠️ 向量模型加载失败: {e}")
            self.model = None

    def build(self, qa_pairs: List[Dict]):
        """构建知识库索引"""
        if self.model is None:
            return
        try:
            import faiss
        except ImportError:
            print("⚠️ faiss未安装")
            return

        grouped = defaultdict(list)
        for pair in qa_pairs:
            key = (pair.get('type', '未分类'), pair.get('environment', '未知'))
            grouped[key].append(pair)

        for key, pairs in grouped.items():
            questions = [p.get('question_content', p.get('question_full', '')) for p in pairs]
            questions = [q for q in questions if q and q.strip()]
            if not questions:
                continue
            try:
                embeddings = self.model.encode(questions)
                index = faiss.IndexFlatL2(embeddings.shape[1])
                index.add(embeddings.astype('float32'))
                self.indexes[key] = index
                self.data[key] = pairs
            except Exception as e:
                print(f"⚠️ 构建索引失败 {key}: {e}")
        print(f"✅ 知识库构建完成: {len(self.indexes)} 个分类")

    def search_with_confidence(self, query: str, q_type: str, env: str, top_k: int = 3) -> Tuple[List[Dict], float]:
        """搜索并返回置信度"""
        if self.model is None or not self.indexes:
            return [], 0.0

        keys_to_try = [(q_type, env), (q_type, '未知'), ('未分类', env), ('未分类', '未知')]

        for key in keys_to_try:
            if key in self.indexes:
                try:
                    vec = self.model.encode([query[:500]])
                    distances, indices = self.indexes[key].search(vec.astype('float32'), top_k)

                    results = []
                    max_confidence = 0.0
                    for idx, dist in zip(indices[0], distances[0]):
                        if idx < len(self.data[key]):
                            confidence = 1.0 / (1.0 + dist / 10)
                            max_confidence = max(max_confidence, confidence)
                            results.append(self.data[key][idx])

                    if results:
                        return results, max_confidence
                except Exception as e:
                    continue
        return [], 0.0