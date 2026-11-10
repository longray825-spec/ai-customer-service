# memory/hierarchical_memory.py
"""层级记忆模块"""

import hashlib
import os
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Any
from models import MemoryItem
from memory.semantic_analyzer import SemanticAnalyzer


class HierarchicalMemory:
    """层级记忆系统"""

    def __init__(self, session_id: str):
        self.session_id = session_id

        # 工作记忆
        self.working_memory: deque = deque(maxlen=10)

        # 短期记忆
        self.short_term_memory: Dict[str, MemoryItem] = {}

        # 中期记忆
        self.mid_term_memory: Dict[str, Any] = {
            'user_preferences': {},
            'common_issues': [],
            'resolution_patterns': [],
            'failed_attempts': []
        }

        # 长期记忆引用
        self.long_term_refs: List[str] = []

        # 语义分析器
        self.analyzer = SemanticAnalyzer()

        # 会话统计
        self.stats = {
            'turn_count': 0,
            'topic_switches': 0,
            'current_topic': None,
            'resolved_issues': []
        }

    def add_interaction(self, user_message: str, bot_response: str, importance: float = 0.3):
        """添加交互"""
        self.working_memory.append({
            'user': user_message,
            'bot': bot_response,
            'timestamp': datetime.now(),
            'importance': importance
        })
        self.stats['turn_count'] += 1

        if importance > 0.7:
            self._promote_to_short_term(user_message, bot_response)

    def _promote_to_short_term(self, user_message: str, bot_response: str):
        """提升到短期记忆"""
        key = hashlib.md5(user_message[:100].encode()).hexdigest()
        if key not in self.short_term_memory:
            self.short_term_memory[key] = MemoryItem(
                content=f"问题: {user_message[:200]}\n解决: {bot_response[:200]}",
                importance=0.7
            )

    def add_failed_attempt(self, question: str, answer: str):
        """记录失败尝试"""
        self.mid_term_memory['failed_attempts'].append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })
        self.mid_term_memory['failed_attempts'] = self.mid_term_memory['failed_attempts'][-20:]

    def add_resolution(self, issue: str, resolution: str):
        """记录成功解决"""
        self.stats['resolved_issues'].append({
            'issue': issue,
            'resolution': resolution,
            'timestamp': datetime.now().isoformat()
        })
        self._update_resolution_patterns(issue, resolution)

    def _update_resolution_patterns(self, issue: str, resolution: str):
        """更新解决模式"""
        pattern = {
            'issue_keywords': self.analyzer.extract_core_meaning(issue),
            'resolution_summary': resolution[:200],
            'count': 1
        }

        found = False
        for p in self.mid_term_memory['resolution_patterns']:
            sim = self.analyzer.calculate_similarity(p['issue_keywords'], pattern['issue_keywords'])
            if sim > 0.7:
                p['count'] += 1
                found = True
                break

        if not found:
            self.mid_term_memory['resolution_patterns'].append(pattern)

        self.mid_term_memory['resolution_patterns'] = self.mid_term_memory['resolution_patterns'][-20:]

    def get_context(self, max_turns: int = 5) -> str:
        """获取上下文"""
        recent = list(self.working_memory)[-max_turns:]
        if not recent:
            return ""

        context = "【会话历史】\n"
        for turn in recent:
            context += f"用户: {turn['user'][:100]}\n"
            context += f"助手: {turn['bot'][:100]}\n"
        return context

    def get_relevant_memories(self, query: str, top_k: int = 3) -> List[MemoryItem]:
        """获取相关记忆"""
        relevant = []

        for key, item in self.short_term_memory.items():
            sim = self.analyzer.calculate_similarity(query, item.content[:100])
            if sim > 0.5:
                relevant.append((sim, item))

        for pattern in self.mid_term_memory['resolution_patterns']:
            sim = self.analyzer.calculate_similarity(query, pattern['issue_keywords'])
            if sim > 0.5:
                relevant.append((sim, MemoryItem(content=f"解决模式: {pattern['resolution_summary']}")))

        relevant.sort(key=lambda x: -x[0])
        return [item for _, item in relevant[:top_k]]

    def get_summary(self) -> str:
        """获取摘要"""
        summary = f"【会话统计】共 {self.stats['turn_count']} 轮对话\n"
        if self.stats['resolved_issues']:
            summary += f"已解决问题: {len(self.stats['resolved_issues'])} 个\n"
        if self.mid_term_memory['failed_attempts']:
            summary += f"失败尝试: {len(self.mid_term_memory['failed_attempts'])} 次\n"
        if self.mid_term_memory['resolution_patterns']:
            summary += f"解决模式: {len(self.mid_term_memory['resolution_patterns'])} 个\n"
        return summary