# human/human_agent.py
"""人工客服模块"""

from collections import deque
from datetime import datetime
from typing import Dict, List


class HumanAgentManager:
    """人工客服管理器"""

    def __init__(self):
        self.waiting_queue = deque()
        self.active_sessions = {}
        self.agent_status = {'available': 3, 'busy': 0, 'total': 3}

    def request_human(self, session_id: str, user_id: str, question: str, conversation_history: List) -> Dict:
        """请求人工客服"""
        ticket = {
            'ticket_id': f"T{datetime.now().strftime('%Y%m%d%H%M%S')}_{session_id[:8]}",
            'session_id': session_id,
            'user_id': user_id,
            'question': question,
            'conversation_history': conversation_history,
            'request_time': datetime.now().isoformat(),
            'status': 'waiting'
        }

        if self.agent_status['available'] > 0:
            ticket['status'] = 'assigned'
            ticket['assigned_time'] = datetime.now().isoformat()
            self.agent_status['available'] -= 1
            self.agent_status['busy'] += 1
            self.active_sessions[session_id] = ticket
            return ticket
        else:
            self.waiting_queue.append(ticket)
            ticket['queue_position'] = len(self.waiting_queue)
            return ticket

    def release_agent(self, session_id: str):
        """释放客服"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self.agent_status['busy'] -= 1
            self.agent_status['available'] += 1

            # 处理等待队列
            if self.waiting_queue and self.agent_status['available'] > 0:
                next_ticket = self.waiting_queue.popleft()
                next_ticket['status'] = 'assigned'
                next_ticket['assigned_time'] = datetime.now().isoformat()
                self.active_sessions[next_ticket['session_id']] = next_ticket
                self.agent_status['available'] -= 1
                self.agent_status['busy'] += 1
                return next_ticket
        return None