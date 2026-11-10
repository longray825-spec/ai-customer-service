# database/user_db.py
"""用户数据库模块"""

import sqlite3
from typing import Optional, Dict


class UserDatabase:
    """用户数据库管理"""

    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 先删除旧表（如果存在且结构不对）
        cursor.execute('DROP TABLE IF EXISTS users')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                account_id TEXT PRIMARY KEY,
                player_name TEXT, 
                device_type TEXT, 
                os_version TEXT,
                app_version TEXT, 
                environment TEXT, 
                region TEXT,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, 
                question TEXT, 
                answer TEXT,
                is_positive BOOLEAN, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS human_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT, 
                user_id TEXT, 
                question TEXT,
                reason TEXT, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入示例数据 - 明确指定列名（不包括 last_login，因为它有默认值）
        sample_users = [
            ('android_67890', 'ケン', 'Xperia 1 II', 'Android 14', '1.1.4', 'Google Play', 'JP'),
            ('ios_12345', 'さくら', 'iPhone 14 Pro', 'iOS 17.2', '1.1.4', 'App Store', 'JP'),
        ]

        # 明确指定列名，只插入7个字段，last_login 使用默认值
        cursor.executemany('''
            INSERT OR IGNORE INTO users 
            (account_id, player_name, device_type, os_version, app_version, environment, region) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_users)

        conn.commit()
        conn.close()
        print("✅ 数据库初始化完成")

    def get_user(self, account_id: str) -> Optional[Dict]:
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT account_id, player_name, device_type, os_version, 
                   app_version, environment, region 
            FROM users WHERE account_id = ?
        ''', (account_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'account_id': row[0],
                'player_name': row[1],
                'device_type': row[2],
                'os_version': row[3],
                'app_version': row[4],
                'environment': row[5],
                'region': row[6]
            }
        return None

    def save_feedback(self, session_id: str, question: str, answer: str, is_positive: bool):
        """保存反馈"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (session_id, question, answer, is_positive) 
            VALUES (?, ?, ?, ?)
        ''', (session_id, question, answer, is_positive))
        conn.commit()
        conn.close()

    def save_human_transfer(self, session_id: str, user_id: str, question: str, reason: str):
        """保存转人工记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO human_transfers (session_id, user_id, question, reason) 
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, question, reason))
        conn.commit()
        conn.close()