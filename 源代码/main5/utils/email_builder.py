# utils/email_builder.py
"""邮件构建和解析模块"""

import re
from datetime import datetime
from typing import Dict
from config import Config


class EmailBuilder:
    """邮件构建器"""

    @staticmethod
    def build(account_id: str, inquiry_type: str, user_message: str, user_info: Dict) -> str:
        """构建邮件内容"""
        type_jp = Config.INQUIRY_TYPE_MAP.get(inquiry_type, inquiry_type)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""お問い合わせ
アカウントID : {account_id}
プレイヤー名 : {user_info.get('player_name', '不明')}
アプリバージョン : {user_info.get('app_version', '不明')}
ご利用のOSバージョン : {user_info.get('os_version', '不明')}
ご利用端末名 : {user_info.get('device_type', '不明')}
お問い合わせ内容の種類 : {type_jp}
ご利用環境 : {user_info.get('environment', '不明')}
問題が発生した日時 : {current_time}
お問い合わせ内容 ：{user_message}"""

    @staticmethod
    def parse_email(email_text: str) -> Dict:
        """解析邮件内容"""
        result = {'type': '未分类', 'environment': '未知', 'content': '', 'device': ''}
        patterns = {
            'type': r'お問い合わせ内容の種類\s*:\s*(.+?)(?:\n|$)',
            'environment': r'ご利用環境\s*:\s*(.+?)(?:\n|$)',
            'device': r'ご利用端末名\s*:\s*(.+?)(?:\n|$)',
            'content': r'お問い合わせ内容\s*：\s*(.+?)$'
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, email_text, re.DOTALL)
            if match:
                result[key] = match.group(1).strip()
        return result