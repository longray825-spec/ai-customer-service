# session/session_manager.py
"""会话管理模块"""

from datetime import datetime
from typing import Dict, List, Tuple
from memory.semantic_analyzer import SemanticAnalyzer
from config import Config


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions = {}
        self.semantic_analyzer = SemanticAnalyzer()
        self.hierarchical_memories = {}

    def get_or_create(self, session_id: str):
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionData(session_id, self.semantic_analyzer)
        return self.sessions[session_id]

    def get_hierarchical_memory(self, session_id: str):
        """获取层级记忆"""
        from memory.hierarchical_memory import HierarchicalMemory
        if session_id not in self.hierarchical_memories:
            self.hierarchical_memories[session_id] = HierarchicalMemory(session_id)
        return self.hierarchical_memories[session_id]

    def record_question(self, session_id: str, question: str, answer: str, confidence: float) -> Dict:
        """记录问题"""
        session = self.get_or_create(session_id)
        return session.record_question(question, answer, confidence)

    def record_feedback(self, session_id: str, is_positive: bool) -> Dict:
        """记录反馈"""
        session = self.get_or_create(session_id)
        return session.record_feedback(is_positive)

    def record_user_choice(self, session_id: str, choice: str) -> Dict:
        """记录用户选择"""
        session = self.get_or_create(session_id)
        return session.record_choice(choice)

    def get_stats(self, session_id: str) -> Dict:
        """获取会话统计"""
        if session_id in self.sessions:
            return self.sessions[session_id].get_stats()
        return {
            'question_count': 0, 'repeat_count': 0, 'repeat_details': [],
            'low_quality_count': 0, 'useless_feedback_count': 0,
            'helpless_keyword_count': 0, 'avg_confidence': 0
        }


class SessionData:
    """会话数据"""

    def __init__(self, session_id: str, analyzer: SemanticAnalyzer):
        self.session_id = session_id
        self.analyzer = analyzer
        self.questions = []
        self.answers = []
        self.confidences = []
        self.core_meanings = []
        self.similarity_scores = []  # 新增：记录每次的相似度
        self.last_offer_human = False
        self.human_offered_at = None
        self.useless_feedback_count = 0
        self.helpless_keyword_count = 0
        self.last_feedback_was_positive = True

    def record_feedback(self, is_positive: bool) -> Dict:
        """记录反馈"""
        result = {
            'should_offer_human': False,
            'offer_reason': None,
            'useless_count': self.useless_feedback_count
        }

        if is_positive:
            self.useless_feedback_count = 0
            self.last_feedback_was_positive = True
        else:
            self.useless_feedback_count += 1
            self.last_feedback_was_positive = False

            if self.useless_feedback_count >= Config.MAX_USELESS_FEEDBACK and not self.last_offer_human:
                result['should_offer_human'] = True
                result['offer_reason'] = f"连续 {self.useless_feedback_count} 次点击「无用」"

        return result

    def _find_semantic_similar(self, new_core: str) -> Tuple[bool, float, int, List[Tuple[int, float]]]:
        """
        查找语义相似的问题
        返回: (是否相似, 最高相似度, 最相似索引, 所有相似对列表)
        """
        if not self.core_meanings:
            return False, 0.0, -1, []

        similarities = []
        for i, old_core in enumerate(self.core_meanings):
            sim = self.analyzer.calculate_similarity(new_core, old_core)
            similarities.append((i, sim))

        # 按相似度排序
        similarities.sort(key=lambda x: -x[1])

        if similarities:
            max_sim = similarities[0][1]
            most_similar_idx = similarities[0][0]
            is_similar = max_sim >= Config.SIMILARITY_THRESHOLD

            # 调试输出
            print(f"   🔍 语义分析: 新问题核心='{new_core[:50]}'")
            print(f"   🔍 最高相似度: {max_sim:.3f} (阈值: {Config.SIMILARITY_THRESHOLD})")
            if len(similarities) > 1:
                print(f"   🔍 第二相似: {similarities[1][1]:.3f}")

            return is_similar, max_sim, most_similar_idx, similarities

        return False, 0.0, -1, []

    def _calculate_repeat_count(self, core_meaning: str) -> Tuple[int, List[Tuple[int, float]]]:
        """
        计算语义重复次数
        返回: (重复次数, 相似对列表)
        """
        if not self.core_meanings:
            return 1, []

        # 计算与所有历史问题的相似度
        similarities = []
        for i, old_core in enumerate(self.core_meanings):
            sim = self.analyzer.calculate_similarity(core_meaning, old_core)
            if sim >= Config.SIMILARITY_THRESHOLD:
                similarities.append((i, sim))

        # 重复次数 = 相似历史数量 + 当前问题
        repeat_count = len(similarities) + 1

        print(f"   🔍 重复计数: 找到 {len(similarities)} 条相似历史，重复次数={repeat_count}")

        return repeat_count, similarities

    def record_choice(self, choice: str) -> Dict:
        """记录用户选择"""
        if choice == "continue_ai":
            self.useless_feedback_count = 0
            self.helpless_keyword_count = 0
            self.last_offer_human = False
            print(f"🔄 用户选择继续AI，已重置触发计数")
            return {"reset": True}
        return {"reset": False}

    # session/session_manager.py - 修改 record_question 方法

    def record_question(self, question: str, answer: str, confidence: float) -> Dict:
        """记录问题 - 增强版，允许重复触发人工"""
        core_meaning = self.analyzer.extract_core_meaning(question)
        contains_helpless = self.analyzer.contains_helpless_keywords(question)

        # 计算语义重复次数
        repeat_count, similar_pairs = self._calculate_repeat_count(core_meaning)

        # 判断是否语义重复
        is_semantic_repeat = repeat_count > 1
        similarity = similar_pairs[0][1] if similar_pairs else 0.0

        # 调试输出
        print(f"\n📝 [Session] 记录问题:")
        print(f"   原始问题: {question[:80]}...")
        print(f"   核心含义: {core_meaning[:60]}...")
        print(f"   语义重复: {is_semantic_repeat}, 重复次数: {repeat_count}")

        # 更新无助关键词计数
        if contains_helpless:
            self.helpless_keyword_count += 1
        else:
            if self.helpless_keyword_count > 0 and not is_semantic_repeat:
                self.helpless_keyword_count = 0

        # 记录当前问题
        self.questions.append(question)
        self.core_meanings.append(core_meaning)
        self.answers.append(answer)
        self.confidences.append(confidence)

        # 计算低质量回答次数
        low_quality_count = sum(1 for c in self.confidences[-5:] if c < Config.CONFIDENCE_THRESHOLD)

        result = {
            'is_repeat': is_semantic_repeat,
            'similarity': similarity,
            'repeat_count': repeat_count,
            'low_quality_count': low_quality_count,
            'total_questions': len(self.questions),
            'contains_helpless': contains_helpless,
            'helpless_keyword_count': self.helpless_keyword_count,
            'should_offer_human': False,
            'offer_reason': None
        }

        # 判断是否需要提供人工选项
        # 移除 last_offer_human 限制，每次都检查
        print(f"\n🔍 [Session] 检查触发条件:")
        print(f"   - 语义重复: {repeat_count}/{Config.MAX_REPEAT_COUNT}")
        print(f"   - 无用反馈: {self.useless_feedback_count}/{Config.MAX_USELESS_FEEDBACK}")
        print(f"   - 无助关键词: {self.helpless_keyword_count}/{Config.MAX_HELPLESS_KEYWORDS}")
        print(f"   - 低质量回答: {low_quality_count}/{Config.MAX_REPEAT_COUNT}")

        if repeat_count >= Config.MAX_REPEAT_COUNT:
            result['should_offer_human'] = True
            result['offer_reason'] = f"相同问题已询问 {repeat_count} 次"
            print(f"🔴 [Session] 触发人工: 语义重复 {repeat_count} 次")

        elif self.useless_feedback_count >= Config.MAX_USELESS_FEEDBACK:
            result['should_offer_human'] = True
            result['offer_reason'] = f"连续 {self.useless_feedback_count} 次点击「无用」"
            print(f"🔴 [Session] 触发人工: 无用反馈 {self.useless_feedback_count} 次")

        elif self.helpless_keyword_count >= Config.MAX_HELPLESS_KEYWORDS:
            result['should_offer_human'] = True
            result['offer_reason'] = f"连续 {self.helpless_keyword_count} 次表示方法无效"
            print(f"🔴 [Session] 触发人工: 无助关键词 {self.helpless_keyword_count} 次")

        elif low_quality_count >= Config.MAX_REPEAT_COUNT:
            result['should_offer_human'] = True
            result['offer_reason'] = f"连续 {low_quality_count} 次未能有效回答"
            print(f"🔴 [Session] 触发人工: 低质量回答 {low_quality_count} 次")

        else:
            print(f"   ✅ 未触发人工")

        # 注意：不再设置 last_offer_human，允许每次都触发
        if result['should_offer_human']:
            self.human_offered_at = datetime.now()
            # 注意：不清空计数，允许继续累积

        return result

    def get_stats(self) -> Dict:
        """获取统计信息"""
        repeat_details = []
        if len(self.core_meanings) > 1:
            processed = set()
            for i, core in enumerate(self.core_meanings):
                if core in processed:
                    continue
                count = sum(1 for c in self.core_meanings
                            if self.analyzer.calculate_similarity(c, core) >= Config.SIMILARITY_THRESHOLD)
                if count > 1:
                    repeat_details.append({'core': core[:50], 'count': count})
                    processed.add(core)

        return {
            'question_count': len(self.questions),
            'repeat_count': max([d['count'] for d in repeat_details]) if repeat_details else 0,
            'repeat_details': repeat_details,
            'low_quality_count': sum(1 for c in self.confidences if c < Config.CONFIDENCE_THRESHOLD),
            'useless_feedback_count': self.useless_feedback_count,
            'helpless_keyword_count': self.helpless_keyword_count,
            'avg_confidence': sum(self.confidences) / len(self.confidences) if self.confidences else 0
        }