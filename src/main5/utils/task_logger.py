# utils/task_logger.py
"""任务日志模块 - 每次启动记录，自动清理旧日志"""

import json
import os
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List
from models import TaskLog


class TaskLogger:
    """任务日志系统 - 每次操作都保存，自动清理旧日志"""

    # 最大保留日志条数（达到此数量时全部清空）
    MAX_LOG_COUNT = 30

    def __init__(self, log_path: str = "task_logs.json"):
        self.log_path = log_path
        self.logs: List[TaskLog] = []
        self._lock = threading.Lock()
        self._load_logs()

        # 启动时清理一次
        self._clean_old_logs()

    def _parse_timestamp(self, timestamp_value) -> datetime:
        """解析时间戳，支持字符串和datetime对象"""
        if timestamp_value is None:
            return datetime.now()
        if isinstance(timestamp_value, datetime):
            return timestamp_value
        if isinstance(timestamp_value, str):
            try:
                return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
            except:
                return datetime.now()
        if isinstance(timestamp_value, (int, float)):
            return datetime.fromtimestamp(timestamp_value)
        return datetime.now()

    def _load_logs(self):
        """加载日志文件"""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    if not data:
                        print("📝 日志文件为空，初始化新日志")
                        self.logs = []
                        return

                    # 转换日志条目为 TaskLog 对象
                    self.logs = []
                    for log in data[-self.MAX_LOG_COUNT:]:
                        try:
                            if 'timestamp' in log:
                                log['timestamp'] = self._parse_timestamp(log['timestamp'])
                            if 'details' not in log:
                                log['details'] = {}
                            self.logs.append(TaskLog(**log))
                        except Exception as e:
                            print(f"⚠️ 跳过损坏的日志条目: {e}")
                            continue

                    print(f"✅ 加载任务日志: {len(self.logs)} 条")

            except json.JSONDecodeError as e:
                print(f"⚠️ 日志文件格式错误: {e}")
                backup_path = f"{self.log_path}.bak"
                if os.path.exists(self.log_path):
                    os.rename(self.log_path, backup_path)
                    print(f"   已备份到: {backup_path}")
                self.logs = []
            except Exception as e:
                print(f"⚠️ 加载日志失败: {e}")
                self.logs = []
        else:
            print("📝 未找到日志文件，将创建新日志")
            self.logs = []

    def _clean_old_logs(self):
        """启动时清理旧日志 - 只保留最近的 MAX_LOG_COUNT 条"""
        if len(self.logs) > self.MAX_LOG_COUNT:
            removed_count = len(self.logs) - self.MAX_LOG_COUNT
            self.logs = self.logs[-self.MAX_LOG_COUNT:]
            print(f"🗑️ 启动清理: 删除了 {removed_count} 条旧日志，保留 {len(self.logs)} 条")
            self._save()

    def log(self, task_log: TaskLog):
        """记录日志 - 达到上限时全部清空"""
        with self._lock:
            # 添加新日志
            self.logs.append(task_log)
            print(f"📝 添加日志: 当前内存中共 {len(self.logs)} 条")

            # 达到上限时全部清空（重新开始）
            if len(self.logs) >= self.MAX_LOG_COUNT:
                removed_count = len(self.logs)
                self.logs = []  # 全部清空
                print(f"🗑️ 日志达到上限({self.MAX_LOG_COUNT})，全部清空，删除了 {removed_count} 条")
            else:
                print(f"📊 当前日志数: {len(self.logs)}/{self.MAX_LOG_COUNT}")

            # 每次都保存
            self._save()

    def _save(self):
        """保存日志到文件 - 完全覆盖写入"""
        try:
            dir_path = os.path.dirname(self.log_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # 准备要保存的数据
            logs_to_save = []
            for log in self.logs:
                if isinstance(log, TaskLog):
                    log_dict = log.__dict__.copy()
                    if 'timestamp' in log_dict and isinstance(log_dict['timestamp'], datetime):
                        log_dict['timestamp'] = log_dict['timestamp'].isoformat()
                    logs_to_save.append(log_dict)
                else:
                    logs_to_save.append(log)

            # 完全覆盖写入文件
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(logs_to_save, f, ensure_ascii=False, indent=2, default=str)

            print(f"💾 日志已保存到文件: {self.log_path} (共 {len(logs_to_save)} 条)")

        except Exception as e:
            print(f"⚠️ 保存日志失败: {e}")

    def clear(self):
        """清空所有日志 - 删除全部"""
        with self._lock:
            removed_count = len(self.logs)
            self.logs = []
            self._save()
            print(f"🗑️ 日志已全部清空: 删除了 {removed_count} 条")

    def get_stats(self, hours: int = 24) -> Dict:
        """获取统计信息"""
        if not self.logs:
            return {"total_requests": 0}

        cutoff = datetime.now().timestamp() - hours * 3600

        recent = []
        for l in self.logs:
            try:
                if isinstance(l.timestamp, datetime):
                    ts = l.timestamp.timestamp()
                elif isinstance(l.timestamp, str):
                    ts = datetime.fromisoformat(l.timestamp.replace('Z', '+00:00')).timestamp()
                else:
                    ts = 0

                if ts > cutoff:
                    recent.append(l)
            except Exception:
                continue

        if not recent:
            return {"total_requests": 0, "note": f"最近{hours}小时内无记录"}

        avg_response_time = sum(l.response_time_ms for l in recent) / len(recent)
        cache_hit_rate = sum(1 for l in recent if l.cache_hit) / len(recent)
        human_transfer_rate = sum(1 for l in recent if l.human_transfer) / len(recent)

        intent_counts = defaultdict(int)
        for l in recent:
            intent_counts[l.intent] += 1

        return {
            "total_requests": len(recent),
            "total_logs": len(self.logs),
            "avg_response_time_ms": round(avg_response_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "human_transfer_rate": round(human_transfer_rate, 3),
            "intent_distribution": dict(intent_counts)
        }

    def get_failed_patterns(self) -> List[Dict]:
        """分析失败模式"""
        failed = [l for l in self.logs if l.human_transfer]
        if not failed:
            return []

        patterns = defaultdict(int)
        for f in failed:
            key = f"{f.intent}_{int(f.confidence * 10)}"
            patterns[key] += 1

        return [{"pattern": k, "count": v} for k, v in sorted(patterns.items(), key=lambda x: -x[1])[:10]]

    def get_recent_logs(self, count: int = 5) -> List[Dict]:
        """获取最近的日志记录"""
        result = []
        for log in self.logs[-count:]:
            if isinstance(log, TaskLog):
                log_dict = log.__dict__.copy()
                if isinstance(log_dict.get('timestamp'), datetime):
                    log_dict['timestamp'] = log_dict['timestamp'].isoformat()
                result.append(log_dict)
            else:
                result.append(log)
        return result