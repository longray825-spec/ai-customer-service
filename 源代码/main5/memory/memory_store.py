# memory/memory_store.py
"""记忆存储模块 - 保留原有的记忆功能"""

import json
import os
from collections import deque
from datetime import datetime
from typing import List, Dict
from config import Config


class MemoryStore:
    """长期记忆存储"""

    def __init__(self):
        self.short_term = deque(maxlen=Config.SHORT_TERM_MEMORY_SIZE)
        self.long_term_file = "memory.json"
        self.long_term = []
        self.failed_cases = []
        self._load()

    def _load(self):
        """加载记忆文件"""
        if os.path.exists(self.long_term_file):
            try:
                with open(self.long_term_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.long_term = data.get('cases', [])
                    self.failed_cases = data.get('failed_cases', [])
                print(f"✅ 加载记忆: {len(self.long_term)} 成功案例, {len(self.failed_cases)} 失败案例")
            except Exception as e:
                print(f"⚠️ 加载记忆失败: {e}")
                self.long_term = []
                self.failed_cases = []
        else:
            print("📝 未找到记忆文件，将创建新记忆")
            self.long_term = []
            self.failed_cases = []

    def _save(self):
        """保存记忆文件"""
        try:
            with open(self.long_term_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cases': self.long_term[-500:],
                    'failed_cases': self.failed_cases[-200:]
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 记忆已保存: {len(self.long_term)} 成功, {len(self.failed_cases)} 失败")
        except Exception as e:
            print(f"⚠️ 保存记忆失败: {e}")

    def add_success(self, question: str, answer: str):
        """添加成功案例"""
        case = {
            "question": question[:200],
            "answer": answer[:200],
            "time": datetime.now().isoformat()
        }
        self.short_term.append(case)
        self.long_term.append(case)
        print(f"📝 添加成功案例: {question[:50]}...")
        print(f"   当前长期记忆数量: {len(self.long_term)}")
        self._save()  # 立即保存，不等待10条

    def add_failure(self, question: str, reason: str):
        """添加失败案例"""
        self.failed_cases.append({
            "question": question[:200],
            "reason": reason,
            "time": datetime.now().isoformat()
        })
        print(f"⚠️ 添加失败案例: {question[:50]}...")
        print(f"   当前失败案例数量: {len(self.failed_cases)}")
        self._save()  # 立即保存

    def get_recent(self, k: int = 3) -> List[Dict]:
        """获取最近的记忆"""
        return list(self.short_term)[-k:]

    def get_failed_cases(self) -> List[Dict]:
        """获取失败案例"""
        return self.failed_cases[-10:]