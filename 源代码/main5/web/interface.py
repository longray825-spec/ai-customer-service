# web/interface.py
"""Web界面模块"""

import gradio as gr
from utils.email_builder import EmailBuilder
from config import Config


def create_web_interface(engine, user_db):
    """创建Gradio Web界面"""

    sessions = {}

    def get_or_create_session(account_id):
        if account_id not in sessions:
            sessions[account_id] = {'id': account_id, 'history': []}
        return sessions[account_id]

    with gr.Blocks(title="游戏客服AI v6.0", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎮 游戏客服AI系统 v6.0 - 高性能优化版
        ### 模糊意图识别 | 混合模型调度 | 响应缓存 | 层级记忆
        """)

        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(height=450, label="对话记录")

                with gr.Group():
                    gr.Markdown("### 📝 新咨询")

                    with gr.Row():
                        account_input = gr.Textbox(label="账户ID", placeholder="例: android_67890", scale=1)
                        type_dropdown = gr.Dropdown(
                            label="咨询类型",
                            choices=["不具合", "アカウント", "課金", "問い合わせ", "意見・要望"],
                            value="課金", scale=1
                        )

                    message_input = gr.Textbox(label="问题描述", lines=4)

                    with gr.Row():
                        send_btn = gr.Button("发送", variant="primary", scale=2)
                        clear_btn = gr.Button("清空", scale=1)

                    gr.Markdown("### 👤 人工服务")
                    with gr.Row():
                        continue_ai_btn = gr.Button("🤖 继续使用AI", variant="secondary", scale=1)
                        transfer_human_btn = gr.Button("👤 转接人工客服", variant="stop", scale=1)

            with gr.Column(scale=1):
                user_info_display = gr.Markdown("### 📋 用户信息\n等待输入...")
                status_display = gr.Markdown("### ⚙️ 状态\n就绪")
                session_stats = gr.Markdown("### 📊 会话统计\n暂无数据")
                perf_stats = gr.Markdown("### ⚡ 性能统计\n等待数据...")

                gr.Markdown("### 👍 反馈")
                with gr.Row():
                    like_btn = gr.Button("👍 有用")
                    dislike_btn = gr.Button("👎 无用")
                feedback_status = gr.Markdown("")

                gr.Markdown("### 💡 转人工触发条件")
                gr.Markdown(f"""
                - 🔄 语义重复 {Config.MAX_REPEAT_COUNT} 次
                - 👎 连续 {Config.MAX_USELESS_FEEDBACK} 次「无用」
                - 💬 连续 {Config.MAX_HELPLESS_KEYWORDS} 次「还是不行」
                """)

        # 隐藏状态
        last_question = gr.State("")
        last_answer = gr.State("")
        current_user = gr.State(None)
        last_metadata = gr.State({})

        def update_perf_stats():
            stats = engine.get_performance_stats()
            model_stats = stats['model_scheduler']
            return f"""### ⚡ 性能统计
- **快速模型**: {model_stats['fast']['calls']}次, 平均{model_stats['fast']['avg_time_ms']:.0f}ms
- **标准模型**: {model_stats['standard']['calls']}次, 平均{model_stats['standard']['avg_time_ms']:.0f}ms
- **高级模型**: {model_stats['premium']['calls']}次, 平均{model_stats['premium']['avg_time_ms']:.0f}ms

**缓存命中率**: {stats['task_logs'].get('cache_hit_rate', 0) * 100:.1f}%
**平均响应**: {stats['task_logs'].get('avg_response_time_ms', 0):.0f}ms"""

        def on_account_change(account_id):
            if not account_id:
                return "### 📋 用户信息\n⚠️ 请输入账户ID", None
            user = user_db.get_user(account_id.strip())
            if user:
                info = f"""### 📋 用户信息
✅ **{user['player_name']}**
- 设备: {user['device_type']}
- OS: {user['os_version']}
- 应用: v{user['app_version']}"""
                return info, user
            return "### 📋 用户信息\n⚠️ 未找到用户", None

        def update_session_stats(account_id):
            if not account_id:
                return "### 📊 会话统计\n请输入账户ID"
            stats = engine.session_manager.get_stats(account_id)
            return f"""### 📊 会话统计
        - 提问次数: {stats['question_count']}
        - 🔄 语义重复: {stats['repeat_count']}次
        - 👎无用点击: {stats['useless_feedback_count']}/{Config.MAX_USELESS_FEEDBACK}
        - 💬无效关键词: {stats['helpless_keyword_count']}/{Config.MAX_HELPLESS_KEYWORDS}
        - 📉 连续 {Config.MAX_REPEAT_COUNT} 次低质量回答（AI置信度低于{Config.CONFIDENCE_THRESHOLD}
        """

        def send_message(history, account_id, inquiry_type, message, user_info):
            if not account_id or not message:
                return history, "⚠️ 请输入完整信息", "", "", "", status, {}, update_session_stats(
                    account_id), update_perf_stats()

            if user_info is None:
                user_info = user_db.get_user(account_id.strip()) or {
                    'account_id': account_id, 'player_name': 'ゲスト',
                    'device_type': '不明', 'os_version': '不明',
                    'app_version': '不明', 'environment': '不明', 'region': 'JP'
                }

            email = EmailBuilder.build(account_id, inquiry_type, message, user_info)
            reply, meta, offer_human = engine.reply(email, session_id=account_id)

            # 构建对话历史
            new_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply}
            ]

            # 如果需要转人工，额外添加一条系统消息（不混入AI回答）
            if offer_human:
                human_message = f"""
        ---
        🔴 **【有人サポートへの転送推奨】**
        {meta.get('offer_reason', 'AIでの対応が難しい状況です')}

        恐れ入りますが、以下のボタンをクリックして**有人客服にお問い合わせ**ください。
        ---
        """
                new_history.append({"role": "assistant", "content": human_message})

            status = f"""### ⚙️ 状态
        ✅ 已回复
        - 意图: {meta.get('intent', '未知')}
        - 使用模型: {meta.get('model_used', 'unknown')}
        - 响应时间: {meta.get('response_time_ms', 0)}ms"""

            return new_history, status, "", message, reply, status, meta, update_session_stats(
                account_id), update_perf_stats()

        def continue_with_ai(account_id, history):
            if account_id:
                # 清除该会话的缓存
                engine.clear_session_cache(account_id)
                print(f"🗑️ 切换回AI模式，清除会话 {account_id} 缓存")

                engine.user_choice(account_id, "continue_ai")
                reply = "✅ AIサポートを継続します。新しい視点で対応いたします。"
                new_history = history + [{"role": "assistant", "content": reply}]
                return new_history, update_session_stats(account_id), "✅ 继续使用AI，已重置记忆"
            return history, update_session_stats(""), "⚠️ 请先输入账户ID"

        def transfer_to_human(account_id, last_q, history):
            if not account_id:
                return history, update_session_stats(""), "⚠️ 需要账户ID"

            # 转人工时也清除缓存，让下次AI重新思考
            engine.clear_session_cache(account_id)

            ticket = engine.human_agent.request_human(account_id, account_id, last_q or "请求人工客服", [])
            reply = f"""オペレーターへの転送リクエストを受け付けました。
        チケット番号: {ticket['ticket_id']}
        {'✅ 担当者がまもなくご連絡いたします。' if ticket['status'] == 'assigned' else f'⏳ お待ちください。順番: {ticket["queue_position"]}番'}"""

            new_history = history + [{"role": "assistant", "content": reply}]
            return new_history, update_session_stats(account_id), f"✅ 已转人工"

        # 绑定事件
        account_input.change(on_account_change, [account_input], [user_info_display, current_user])
        account_input.change(update_session_stats, [account_input], [session_stats])

        send_btn.click(send_message, [chatbot, account_input, type_dropdown, message_input, current_user],
                       [chatbot, status_display, message_input, last_question, last_answer, session_stats,
                        last_metadata, session_stats, perf_stats])

        continue_ai_btn.click(continue_with_ai, [account_input, chatbot], [chatbot, session_stats, feedback_status])
        transfer_human_btn.click(transfer_to_human, [account_input, last_question, chatbot],
                                 [chatbot, session_stats, feedback_status])

        def clear_all():
            return [], "### ⚙️ 状态\n就绪", "", "", "", "### 📊 会话统计\n暂无数据", {}, update_perf_stats()

        clear_btn.click(clear_all, None,
                        [chatbot, status_display, message_input, last_question, last_answer, session_stats,
                         last_metadata, perf_stats])

        like_btn.click(lambda q, a, acc: (engine.feedback(acc, q, a, True), "✅ 感谢反馈！")[1],
                       [last_question, last_answer, account_input], [feedback_status])
        dislike_btn.click(lambda q, a, acc: (engine.feedback(acc, q, a, False), "👎 已记录")[1],
                          [last_question, last_answer, account_input], [feedback_status])

    return demo