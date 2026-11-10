# engine.py
"""客服引擎 - 核心业务逻辑"""

import os
import time
import datetime  # 添加 datetime 导入
from typing import Tuple, Dict
import pandas as pd

from config import Config
from models import TaskLog
from llm.knowledge_base import KnowledgeBase
from llm.model_scheduler import HybridModelScheduler
from llm.cache import ResponseCache
from memory.memory_store import MemoryStore
from memory.hierarchical_memory import HierarchicalMemory
from memory.vector_memory import get_vector_memory
from intent.intent_recognizer import FuzzyIntentRecognizer
from session.session_manager import SessionManager
from human.human_agent import HumanAgentManager
from utils.email_builder import EmailBuilder
from utils.task_logger import TaskLogger
from utils.time_aware import TimeAware


class CustomerServiceEngine:
    """客服引擎核心类"""

    def __init__(self, excel_path: str):
        print("\n" + "=" * 50)
        print("🚀 正在初始化客服系统 v6.0...")
        print("=" * 50)

        # 检查配置
        Config.check_config()

        # 如果 API Key 未设置，给出警告
        if not Config.DASHSCOPE_API_KEY:
            print("⚠️ 警告: DASHSCOPE_API_KEY 未设置！")
            print("   将使用降级响应模式，回答会比较简短。")
            print("   请设置环境变量: export DASHSCOPE_API_KEY='your_key'")
            print()

        # 初始化各模块
        self.knowledge_base = KnowledgeBase()
        self.memory_store = MemoryStore()
        self.time_aware = TimeAware()
        self.human_agent = HumanAgentManager()
        self.session_manager = SessionManager()

        # 新增优化组件
        self.intent_recognizer = FuzzyIntentRecognizer()
        self.model_scheduler = HybridModelScheduler()
        self.response_cache = ResponseCache()
        self.task_logger = TaskLogger()

        # 加载数据
        self.qa_pairs = self._load_data(excel_path)
        if self.qa_pairs:
            self.knowledge_base.build(self.qa_pairs)

        # 向量记忆
        self.vector_memory = get_vector_memory()
        print(f"✅ 系统初始化完成，共 {len(self.qa_pairs)} 条知识")
        print(f"✅ 向量记忆初始化完成，当前存储: {self.vector_memory.get_stats()['total_memories']} 条")
        print("=" * 50 + "\n")

    def _load_data(self, excel_path: str) -> list:
        """加载知识库数据"""
        try:
            if not os.path.exists(excel_path):
                print(f"⚠️ 数据文件不存在: {excel_path}")
                return self._get_sample_data()

            df = pd.read_excel(excel_path)
            print(f"📁 读取数据: {len(df)} 行")

            qa_pairs = []
            if 'メールID' in df.columns:
                for mail_id, group in df.groupby('メールID'):
                    question_rows = group[group['メールID枝番'] == 1]
                    answer_rows = group[group['メールID枝番'] == 2]
                    if len(question_rows) == 0 or len(answer_rows) == 0:
                        continue
                    q_text = question_rows.iloc[0].get('本文', '')
                    a_text = answer_rows.iloc[0].get('本文', '')
                    if not isinstance(q_text, str) or not q_text.strip():
                        continue
                    parsed = EmailBuilder.parse_email(q_text)
                    qa_pairs.append({
                        'mail_id': mail_id,
                        'question_full': q_text,
                        'question_content': parsed.get('content', q_text[:200]),
                        'answer': a_text,
                        'type': parsed.get('type', '未分类'),
                        'environment': parsed.get('environment', '未知')
                    })
            print(f"✅ 构建问答对: {len(qa_pairs)} 条")
            return qa_pairs if qa_pairs else self._get_sample_data()
        except Exception as e:
            print(f"⚠️ 数据加载失败: {e}")
            return self._get_sample_data()

    def _get_sample_data(self) -> list:
        """获取示例数据"""
        print("📚 使用示例知识库")
        return [
            {'mail_id': 'sample_001', 'question_full': 'ゲームがフリーズする',
             'question_content': 'ゲームがフリーズする', 'type': '不具合', 'environment': 'Android',
             'answer': '大変申し訳ございません。以下の対処法をお試しください：\n1. アプリを再起動する\n2. 端末を再起動する\n3. アプリを最新版に更新する\n4. キャッシュを削除する'},
            {'mail_id': 'sample_002', 'question_full': '課金したのにアイテムが届かない',
             'question_content': '課金したのにアイテムが届かない', 'type': '課金', 'environment': 'iOS',
             'answer': 'ご連絡ありがとうございます。以下の情報をご提供ください：\n1. アカウントID\n2. 購入日時\n3. 購入金額\n4. レシートのスクリーンショット'}
        ]

    def reply(self, email_content: str, session_id: str = None) -> Tuple[str, Dict, bool]:
        """处理用户回复"""
        start_time = time.time()
        parsed = EmailBuilder.parse_email(email_content)
        user_message = parsed['content']

        # 1. 意图识别
        intent_result = self.intent_recognizer.recognize(user_message)
        print(f"🎯 意图识别: {intent_result.primary_intent} (置信度: {intent_result.confidence:.2f})")

        # ========== 向量记忆检索 ==========
        history_attempts = self.vector_memory.get_attempted_steps_from_history(
            user_message, session_id
        )

        if history_attempts['source_count'] > 0:
            print(f"📚 向量记忆: 找到 {history_attempts['source_count']} 条相关历史")
            print(f"   已尝试步骤: {history_attempts['attempted']}")
            print(f"   无效步骤: {history_attempts['failed']}")
        # =================================

        # 2. 检查缓存
        cached_response = self.response_cache.get(
            user_message,
            intent_result.primary_intent,
            session_id
        )

        cache_hit = False
        if cached_response:
            cache_hit = True
            answer = cached_response
            confidence = 0.8
            similar = []
        else:
            # 3. 知识库检索
            similar, confidence = self.knowledge_base.search_with_confidence(
                user_message, parsed['type'], parsed['environment']
            )

            # 4. 获取层级记忆上下文
            hierarchical_memory = self.session_manager.get_hierarchical_memory(session_id) if session_id else None
            memory_context = ""
            if hierarchical_memory:
                memory_context = hierarchical_memory.get_context()
                relevant_memories = hierarchical_memory.get_relevant_memories(user_message)
                if relevant_memories:
                    memory_context += "\n【相关记忆】\n" + "\n".join([m.content[:200] for m in relevant_memories])

            # 5. 计算复杂度并选择模型
            complexity = self.model_scheduler.estimate_complexity(user_message, intent_result)
            model_type = self.model_scheduler.select_model(complexity)
            print(f"🤖 复杂度: {complexity:.2f}, 选择模型: {model_type.value}")

            # 6. 构建提示词
            prompt = self._build_prompt_with_vector_memory(
                email_content, parsed, similar,
                self.memory_store.get_recent(),
                self.time_aware.get_style()[1],
                confidence, memory_context, intent_result,
                history_attempts
            )

            # 7. 调用模型
            answer, response_time = self.model_scheduler.call_model(prompt, model_type)

            # 8. 缓存响应
            self.response_cache.set(
                user_message,
                intent_result.primary_intent,
                answer,
                session_id
            )

        # 9. 会话管理和人工触发检测
        offer_human = False
        offer_reason = None
        repeat_count = 0

        if session_id:
            session_result = self.session_manager.record_question(
                session_id, user_message, answer, confidence
            )
            offer_human = session_result['should_offer_human']
            offer_reason = session_result.get('offer_reason')
            repeat_count = session_result.get('repeat_count', 0)

            # 层级记忆
            hierarchical_memory = self.session_manager.get_hierarchical_memory(session_id)
            hierarchical_memory.add_interaction(user_message, answer,
                                                importance=1.0 if offer_human else 0.3)

            # ========== 保存到向量记忆 ==========
            attempted_steps = self.vector_memory._extract_attempted_steps(user_message)
            self.vector_memory.add_conversation(
                session_id=session_id,
                user_message=user_message,
                bot_response=answer,
                attempted_steps=attempted_steps,
                issue_type=intent_result.primary_intent
            )
            # =================================

        # 10. 添加人工选项
        if offer_human and not self.session_manager.get_or_create(session_id).last_offer_human:
            answer += self._get_human_option_message(offer_reason)

        # 11. 记录任务日志
        elapsed_ms = (time.time() - start_time) * 1000
        task_log = TaskLog(
            task_id=f"{session_id}_{int(time.time())}" if session_id else "unknown",
            session_id=session_id or "unknown",
            intent=intent_result.primary_intent,
            confidence=confidence,
            response_time_ms=elapsed_ms,
            model_used="cache" if cache_hit else model_type.value,
            cache_hit=cache_hit,
            human_transfer=offer_human,
            details={
                'vector_memory_hits': history_attempts['source_count']
            }
        )
        self.task_logger.log(task_log)

        metadata = {
            'type': parsed['type'],
            'env': parsed['environment'],
            'similar_count': len(similar),
            'confidence': confidence,
            'offer_human': offer_human,
            'offer_reason': offer_reason,
            'repeat_count': repeat_count,
            'intent': intent_result.primary_intent,
            'model_used': "cache" if cache_hit else model_type.value,
            'response_time_ms': round(elapsed_ms, 2),
            'vector_memory_hits': history_attempts['source_count']
        }

        return answer, metadata, offer_human

    def _build_prompt_with_vector_memory(self, email: str, parsed: Dict, similar: list,
                                         memories: list, style_desc: str, confidence: float,
                                         memory_context: str, intent_result,
                                         history_attempts: Dict) -> str:
        """构建包含向量记忆的提示词"""
        # 构建已尝试步骤的提示
        attempted_section = ""
        if history_attempts.get('attempted'):
            step_names = {
                'app_restart': 'アプリ再起動',
                'device_restart': '端末再起動',
                'cache_clear': 'キャッシュ削除',
                'app_update': 'アプリ更新',
                'reinstall': '再インストール',
                'data_repair': 'データ修復'
            }

            attempted_jp = [step_names.get(s, s) for s in history_attempts['attempted']]
            failed_jp = [step_names.get(s, s) for s in history_attempts.get('failed', [])]

            attempted_section = f"""
【過去の類似問題からの情報 - 重要】
過去の類似した質問から、このユーザーは以下の方法を**既に試しています**：

試した方法: {', '.join(attempted_jp)}

"""
            if failed_jp:
                attempted_section += f"""
効果がなかった方法: {', '.join(failed_jp)}

"""

            attempted_section += """
【厳守事項】
上記の方法を再度提案することは**絶対に禁止**します。
ユーザーがまだ試していない、より高度な解決策を提案してください。
"""

        similar_text = ""
        for i, s in enumerate(similar[:2]):
            q = s.get('question_content', s.get('question_full', ''))[:150]
            a = s.get('answer', '')[:300]
            similar_text += f"\n【参考案例{i + 1}】\n用户: {q}\n客服回答: {a}\n"

        memory_text = ""
        for m in memories:
            memory_text += f"\n成功案例: {m['question']} -> {m['answer']}"

        return f"""あなたはプロの日本のゲームカスタマーサポートです。丁寧な日本語（です・ます調）で回答してください。

{attempted_section}

【ユーザー情報】
種別: {parsed['type']} | 環境: {parsed['environment']} | デバイス: {parsed['device']}

【意図分析】
主要意図: {intent_result.primary_intent} (確信度: {intent_result.confidence:.2f})

【回答スタイル】{style_desc}

【会話履歴】
{memory_context}

【ユーザーのお問い合わせ】
{email}

【参考事例】{similar_text}

【過去の成功事例】{memory_text}

【回答ルール】
1. ユーザーが既に試した方法は絶対に提案しない（最も重要）
2. 段階的に、より高度な解決策を提供する
3. 具体的で実用的なアドバイスを提供する
4. 不具合の場合は、ステップバイステップで説明する

回答（日本語のみ）:"""

    def _get_human_option_message(self, reason: str = None) -> str:
        """获取人工选项消息 - 简洁直观版"""

        now = datetime.datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # 服务时间：8:30 - 17:30
        is_service_time = (current_hour > 8 or (current_hour == 8 and current_minute >= 30)) and \
                          (current_hour < 17 or (current_hour == 17 and current_minute <= 30))

        message = "\n\n"
        message += "=" * 50 + "\n"
        message += "🔴 現在の質問はAIの対応範囲を超えています 🔴\n"
        message += "=" * 50 + "\n\n"

        message += "恐れ入りますが、下記の内容を添えて\n"
        message += "**有人客服にお問い合わせください**。\n\n"

        message += "📝 お問い合わせ内容：\n"
        message += f"   {reason if reason else '上記の質問内容'}\n\n"

        if is_service_time:
            message += "✅ 現在、有人サポート対応可能時間です。\n"
            message += "   お問い合わせ内容を確認次第、担当者よりご連絡いたします。\n"
        else:
            message += "⏰ 現在、有人サポート対応時間外です。\n"
            message += "   営業時間: 平日 8:30 - 17:30\n"
            message += "   翌営業日にご連絡いたします。ご不便をおかけして申し訳ございません。\n"

        message += "\n" + "=" * 50

        return message

    def _build_prompt(self, email: str, parsed: Dict, similar: list, memories: list,
                      style_desc: str, confidence: float, memory_context: str, intent_result) -> str:
        """构建提示词（备用）"""
        similar_text = ""
        for i, s in enumerate(similar[:2]):
            q = s.get('question_content', s.get('question_full', ''))[:150]
            a = s.get('answer', '')[:300]
            similar_text += f"\n【参考案例{i + 1}】\n用户: {q}\n客服回答: {a}\n"

        memory_text = ""
        for m in memories:
            memory_text += f"\n成功案例: {m['question']} -> {m['answer']}"

        return f"""あなたはプロの日本のゲームカスタマーサポートです。丁寧な日本語（です・ます調）で回答してください。

【ユーザー情報】
種別: {parsed['type']} | 環境: {parsed['environment']} | デバイス: {parsed['device']}

【意図分析】
主要意図: {intent_result.primary_intent} (確信度: {intent_result.confidence:.2f})
検出キーワード: {', '.join(intent_result.keywords_found[:5])}

【回答スタイル】{style_desc}

【会話履歴】
{memory_context}

【ユーザーのお問い合わせ】
{email}

【参考事例】{similar_text}

【過去の成功事例】{memory_text}

【回答ルール】
1. 具体的で実用的な解決策を提供する
2. 不具合：具体的な手順をステップバイステップで説明
3. 課金問題：確認に必要な情報を具体的に列挙
4. 同じ質問が繰り返されている場合は、別の解決策を提案する

回答（日本語のみ）:"""

    def feedback(self, session_id: str, question: str, answer: str, is_positive: bool):
        """记录用户反馈"""
        print(f"🔧 反馈记录: session={session_id}, is_positive={is_positive}")

        if session_id:
            result = self.session_manager.record_feedback(session_id, is_positive)
            hierarchical_memory = self.session_manager.get_hierarchical_memory(session_id)
            if is_positive:
                hierarchical_memory.add_resolution(question, answer)
            else:
                hierarchical_memory.add_failed_attempt(question, answer)

        if is_positive:
            self.memory_store.add_success(question, answer)
        else:
            self.memory_store.add_failure(question, "用户反馈负面")

    def user_choice(self, session_id: str, choice: str) -> Dict:
        """用户选择处理"""
        return self.session_manager.record_user_choice(session_id, choice)

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        return {
            'model_scheduler': self.model_scheduler.get_stats(),
            'task_logs': self.task_logger.get_stats()
        }

    def get_vector_memory_stats(self) -> Dict:
        """获取向量记忆统计"""
        return self.vector_memory.get_stats()

    def clear_session_cache(self, session_id: str):
        """清除指定会话的缓存"""
        self.response_cache.clear_session_cache(session_id)