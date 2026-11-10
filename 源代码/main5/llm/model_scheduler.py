# llm/model_scheduler.py
"""混合模型调度器"""

import time
from collections import defaultdict
from typing import Tuple, Dict
from models import ModelType
from config import Config


class HybridModelScheduler:
    """混合模型调度器"""

    def __init__(self):
        self.model_configs = {
            ModelType.FAST: {
                'name': 'qwen-turbo',
                'max_tokens': 500,
                'timeout': 30.0,
                'cost_per_1k': 0.004
            },
            ModelType.STANDARD: {
                'name': 'qwen-plus',
                'max_tokens': 800,
                'timeout': 30.0,
                'cost_per_1k': 0.004
            },
            ModelType.PREMIUM: {
                'name': 'qwen3-max',
                'max_tokens': 1200,
                'timeout': 45.0,
                'cost_per_1k': 0.02
            }
        }

        self.stats = defaultdict(lambda: {'calls': 0, 'total_time': 0})

    def estimate_complexity(self, query: str, intent) -> float:
        """估算问题复杂度 (0-1) - 修复版"""
        complexity = 0.0

        # 1. 长度因素（更敏感）
        length = len(query)
        if length > 300:
            complexity += 0.4
        elif length > 150:
            complexity += 0.25
        elif length > 60:
            complexity += 0.15
        elif length > 20:
            complexity += 0.05

        # 2. 意图置信度因素（反向，低置信度增加复杂度）
        # 置信度低于0.7时开始增加复杂度
        intent_conf = getattr(intent, 'confidence', 0.5)
        if intent_conf < 0.3:
            complexity += 0.4
        elif intent_conf < 0.5:
            complexity += 0.25
        elif intent_conf < 0.7:
            complexity += 0.15
        elif intent_conf < 0.85:
            complexity += 0.05

        # 3. 技术关键词因素（多个关键词累加）
        tech_keywords = ['エラー', 'バグ', 'クラッシュ', 'エラーコード',
                         'フリーズ', '動かない', '不具合', '障害']
        tech_count = 0
        for kw in tech_keywords:
            if kw in query:
                tech_count += 1
        complexity += min(tech_count * 0.1, 0.3)  # 最多加0.3

        # 4. 多意图因素
        alt_intents = getattr(intent, 'alternative_intents', [])
        if len(alt_intents) >= 2:
            complexity += 0.2
        elif len(alt_intents) >= 1:
            complexity += 0.1

        # 5. 疑问词/求助词因素（表明用户需要详细帮助）
        help_keywords = ['どうすれば', '教えて', '助けて', '方法', '解決',
                         '対処法', '原因', 'なぜ', '何とか']
        for kw in help_keywords:
            if kw in query:
                complexity += 0.05
                break

        # 6. 紧急程度因素
        urgent_keywords = ['至急', '早急', '困って', '大変', 'すぐに', '今すぐ']
        for kw in urgent_keywords:
            if kw in query:
                complexity += 0.1
                break

        # 限制最大值为1.0
        result = min(complexity, 1.0)

        # 调试输出
        print(f"   📊 复杂度分解: 长度={length}(+{self._get_length_score(length)}), "
              f"置信度={intent_conf:.2f}(+{self._get_confidence_score(intent_conf)}), "
              f"技术词={tech_count}(+{min(tech_count * 0.1, 0.3)}), "
              f"多意图={len(alt_intents)}(+{0.2 if len(alt_intents) >= 2 else (0.1 if len(alt_intents) >= 1 else 0)}), "
              f"总计={result:.3f}")

        return result

    def _get_length_score(self, length: int) -> float:
        """获取长度分数"""
        if length > 300:
            return 0.4
        elif length > 150:
            return 0.25
        elif length > 60:
            return 0.15
        elif length > 20:
            return 0.05
        return 0.0

    def _get_confidence_score(self, confidence: float) -> float:
        """获取置信度分数（越低越复杂）"""
        if confidence < 0.3:
            return 0.4
        elif confidence < 0.5:
            return 0.25
        elif confidence < 0.7:
            return 0.15
        elif confidence < 0.85:
            return 0.05
        return 0.0

    def select_model(self, complexity: float) -> ModelType:
        """根据复杂度选择模型 - 调整阈值"""
        # 调低阈值，让更多问题进入高级模型
        if complexity < 0.30:  # 极简单问题
            return ModelType.FAST
        elif complexity < 0.45:  # 一般问题
            return ModelType.STANDARD
        else:  # 复杂问题
            return ModelType.PREMIUM

    def call_model(self, prompt: str, model_type: ModelType, timeout: float = None) -> Tuple[str, float]:
        """调用模型，返回(响应, 响应时间ms)"""
        config = self.model_configs[model_type]
        timeout = timeout or config['timeout']

        start_time = time.time()

        try:
            if Config.DASHSCOPE_API_KEY:
                from openai import OpenAI
                client = OpenAI(
                    api_key=Config.DASHSCOPE_API_KEY,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    timeout=timeout
                )

                resp = client.chat.completions.create(
                    model=config['name'],
                    messages=[{"role": "user", "content": prompt[:3000]}],
                    temperature=0.7,
                    max_tokens=config['max_tokens']
                )

                response = resp.choices[0].message.content.strip()
                elapsed_ms = (time.time() - start_time) * 1000

                self.stats[model_type]['calls'] += 1
                self.stats[model_type]['total_time'] += elapsed_ms

                print(f"   ✅ 模型响应: {len(response)}字符, 耗时{elapsed_ms:.0f}ms")
                return response, elapsed_ms
            else:
                print(f"   ⚠️ 无API Key，使用降级响应")
                return self._fallback_response(prompt), 50.0

        except Exception as e:
            print(f"   ❌ 模型调用失败 ({model_type.value}): {e}")
            if model_type != ModelType.FAST:
                print(f"   🔄 降级到快速模型...")
                return self.call_model(prompt, ModelType.FAST, timeout)
            return self._fallback_response(prompt), 100.0

    def _fallback_response(self, prompt: str) -> str:
        """降级响应 - 生成更完整的回答"""
        if "フリーズ" in prompt or "崩溃" in prompt or "動かない" in prompt:
            return """大変申し訳ございません。ゲームがフリーズする問題について、以下の対処法をお試しください。

【対処手順】
1. アプリを再起動する
2. 端末を再起動する
3. アプリを最新版に更新する
4. キャッシュを削除する

それでも解決しない場合は、端末モデルとOSバージョンをお知らせください。
ご不便をおかけして申し訳ございません。"""

        elif "課金" in prompt or "充值" in prompt or "購入" in prompt or "届かない" in prompt:
            return """ご連絡ありがとうございます。購入アイテムが届いていないとのこと、大変申し訳ございません。

以下の情報をご提供いただけますと幸いです：
・アカウントID
・購入日時
・購入金額
・購入時のレシート

ご提供いただいた情報をもとに、担当部門にて確認させていただきます。"""

        elif "アカウント" in prompt or "登录" in prompt or "ログイン" in prompt:
            return """アカウントに関するお問い合わせありがとうございます。

アカウントIDをお知らせいただければ、担当部門にて確認させていただきます。
ご不明な点がございましたら、お気軽にお知らせください。"""

        else:
            return """お問い合わせありがとうございます。

いただいたご質問について、担当部門に確認の上、追ってご連絡いたします。
この度はご不便をおかけして申し訳ございません。"""

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'fast': {
                'calls': self.stats[ModelType.FAST]['calls'],
                'avg_time_ms': self.stats[ModelType.FAST]['total_time'] / max(1, self.stats[ModelType.FAST]['calls'])
            },
            'standard': {
                'calls': self.stats[ModelType.STANDARD]['calls'],
                'avg_time_ms': self.stats[ModelType.STANDARD]['total_time'] / max(1, self.stats[ModelType.STANDARD][
                    'calls'])
            },
            'premium': {
                'calls': self.stats[ModelType.PREMIUM]['calls'],
                'avg_time_ms': self.stats[ModelType.PREMIUM]['total_time'] / max(1,
                                                                                 self.stats[ModelType.PREMIUM]['calls'])
            }
        }