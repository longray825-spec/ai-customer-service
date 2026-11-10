# memory/vector_memory.py
"""向量记忆模块 - 使用向量数据库存储和检索对话历史"""

import json
import os
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# 尝试导入向量相关库
try:
    from sentence_transformers import SentenceTransformer
    import faiss

    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    print("⚠️ sentence-transformers 或 faiss 未安装，向量记忆功能不可用")
    print("   请运行: pip install sentence-transformers faiss-cpu")


class VectorMemory:
    """
    向量记忆系统 - 存储和检索对话历史

    功能：
    1. 将每个对话轮次向量化存储
    2. 新问题到来时，检索相似的历史对话
    3. 提取用户已尝试过的方法，避免重复建议
    """

    def __init__(self, storage_path: str = "vector_memory.json"):
        self.storage_path = storage_path
        self.model = None
        self.index = None
        self.memories: List[Dict] = []  # 存储原始数据
        self.vectors: List[np.ndarray] = []  # 存储向量

        # 维度（MiniLM 输出 384 维）
        self.dimension = 384

        self._init_model()
        self._load()

    def _init_model(self):
        """初始化向量模型"""
        if not VECTOR_AVAILABLE:
            return

        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✅ 向量模型加载完成，维度: {self.dimension}")
        except Exception as e:
            print(f"⚠️ 向量模型加载失败: {e}")
            self.model = None

    def _load(self):
        """从文件加载记忆"""
        if not os.path.exists(self.storage_path):
            print("📝 未找到向量记忆文件，将创建新文件")
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.memories = data.get('memories', [])
                # 向量需要单独处理，因为 numpy 数组不能直接 JSON 序列化
                vectors_data = data.get('vectors', [])
                self.vectors = [np.array(v) for v in vectors_data] if vectors_data else []

                # 如果没有保存向量，尝试重建
                if not self.vectors and self.memories and self.model:
                    self._rebuild_vectors()

                print(f"✅ 加载向量记忆: {len(self.memories)} 条")
        except Exception as e:
            print(f"⚠️ 加载向量记忆失败: {e}")
            self.memories = []
            self.vectors = []

    def _rebuild_vectors(self):
        """重建所有向量（当从旧格式加载时）"""
        if not self.model:
            return

        print(f"🔄 正在重建 {len(self.memories)} 条记忆的向量...")
        texts = [m['user_message'] for m in self.memories]
        self.vectors = self.model.encode(texts).tolist()
        self._save()
        print("✅ 向量重建完成")

    def _save(self):
        """保存记忆到文件"""
        try:
            # 将 numpy 数组转换为列表以便 JSON 序列化
            vectors_list = [v.tolist() if isinstance(v, np.ndarray) else v for v in self.vectors]

            data = {
                'memories': self.memories,
                'vectors': vectors_list,
                'updated_at': datetime.now().isoformat()
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 只保留最近 500 条
            if len(self.memories) > 500:
                self.memories = self.memories[-500:]
                self.vectors = self.vectors[-500:]
                self._save()

        except Exception as e:
            print(f"⚠️ 保存向量记忆失败: {e}")

    def add_conversation(self, session_id: str, user_message: str, bot_response: str,
                         attempted_steps: List[str] = None, issue_type: str = None):
        """
        添加对话轮次到向量记忆

        参数:
            session_id: 会话ID
            user_message: 用户消息
            bot_response: 机器人回复
            attempted_steps: 用户已尝试的步骤列表
            issue_type: 问题类型（freeze/payment/account等）
        """
        if not self.model:
            return

        # 提取已尝试的步骤
        if attempted_steps is None:
            attempted_steps = self._extract_attempted_steps(user_message)

        # 创建记忆条目
        memory = {
            'session_id': session_id,
            'user_message': user_message[:500],
            'bot_response': bot_response[:500],
            'attempted_steps': attempted_steps,
            'issue_type': issue_type or self._detect_issue_type(user_message),
            'timestamp': datetime.now().isoformat(),
            'was_successful': None  # 后续可通过反馈更新
        }

        # 生成向量
        vector = self.model.encode([user_message])[0]

        self.memories.append(memory)
        self.vectors.append(vector)

        # 只保留最近 500 条
        if len(self.memories) > 500:
            self.memories = self.memories[-500:]
            self.vectors = self.vectors[-500:]

        self._save()
        print(f"📝 向量记忆已添加: {user_message[:50]}...")

    def _extract_attempted_steps(self, message: str) -> List[str]:
        """从消息中提取用户已尝试的步骤"""
        steps = []

        keywords_map = {
            'app_restart': ['再起動', 'restart', '重启', '重新启动'],
            'device_restart': ['端末再起動', '電源', '关机', 'power off'],
            'cache_clear': ['キャッシュ', 'cache', '缓存', '清除缓存'],
            'app_update': ['更新', 'アップデート', 'update', '升级'],
            'reinstall': ['再インストール', 'reinstall', '重装', '重新安装'],
            'data_repair': ['修復', 'repair', '修复'],
        }

        for step, keywords in keywords_map.items():
            for kw in keywords:
                if kw in message:
                    steps.append(step)
                    break

        return steps

    def _detect_issue_type(self, message: str) -> str:
        """检测问题类型"""
        if any(kw in message for kw in ['フリーズ', '動かない', 'クラッシュ', '崩溃', '卡顿']):
            return 'freeze'
        elif any(kw in message for kw in ['課金', '購入', '届かない', '充值', '购买']):
            return 'payment'
        elif any(kw in message for kw in ['アカウント', 'ログイン', '账号', '登录']):
            return 'account'
        else:
            return 'general'

    def retrieve_similar(self, query: str, session_id: str = None,
                         top_k: int = 3, similarity_threshold: float = 0.6) -> List[Dict]:
        """
        检索相似的对话历史

        参数:
            query: 查询文本
            session_id: 可选，同一会话的权重更高
            top_k: 返回数量
            similarity_threshold: 相似度阈值

        返回:
            相似记忆列表，按相似度排序
        """
        if not self.model or not self.vectors:
            return []

        # 生成查询向量
        query_vector = self.model.encode([query])[0]

        # 计算相似度
        scored = []
        for i, vec in enumerate(self.vectors):
            # 余弦相似度
            sim = np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))

            # 同一会话的权重提高 1.3 倍
            if session_id and self.memories[i]['session_id'] == session_id:
                sim *= 1.3

            scored.append((sim, i))

        # 排序
        scored.sort(key=lambda x: -x[0])

        # 返回相似度高于阈值的结果
        results = []
        for sim, idx in scored[:top_k]:
            if sim >= similarity_threshold:
                result = self.memories[idx].copy()
                result['similarity'] = round(sim, 3)
                results.append(result)

        print(f"🔍 向量检索: '{query[:30]}...' 找到 {len(results)} 条相似记忆")
        return results

    def get_attempted_steps_from_history(self, query: str, session_id: str = None) -> Dict:
        """
        从历史记忆中提取用户已尝试的步骤

        返回:
            {
                'attempted': ['app_restart', 'cache_clear'],
                'failed': ['app_restart'],  # 明确表示无效的
                'source_count': 3  # 找到的相关记忆数量
            }
        """
        similar = self.retrieve_similar(query, session_id, top_k=5)

        attempted = set()
        failed = set()

        for mem in similar:
            for step in mem.get('attempted_steps', []):
                attempted.add(step)

                # 检查用户是否明确表示该方法无效
                user_msg = mem.get('user_message', '')
                if any(word in user_msg for word in ['ダメ', '無理', 'できない', '効果なし', '不行', '没用']):
                    failed.add(step)

        return {
            'attempted': list(attempted),
            'failed': list(failed),
            'source_count': len(similar)
        }

    def update_feedback(self, user_message: str, is_positive: bool):
        """更新记忆的反馈（标记解决方案是否有效）"""
        # 找到最近匹配的记忆并更新
        similar = self.retrieve_similar(user_message, top_k=1)
        if similar:
            # 在实际应用中，可以通过 ID 精确定位
            print(f"📝 反馈更新: {'成功' if is_positive else '失败'} -> {user_message[:50]}...")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_memories': len(self.memories),
            'has_model': self.model is not None,
            'storage_path': self.storage_path,
            'issue_breakdown': dict(
                defaultdict(int,
                            [(m['issue_type'], defaultdict(int, [('count', 1)])['count'])
                             for m in self.memories]
                            )
            ) if self.memories else {}
        }


# 全局单例
_global_vector_memory = None


def get_vector_memory() -> VectorMemory:
    """获取全局向量记忆实例"""
    global _global_vector_memory
    if _global_vector_memory is None:
        _global_vector_memory = VectorMemory()
    return _global_vector_memory