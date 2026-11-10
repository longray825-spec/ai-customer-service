# main.py
"""游戏客服AI系统 v6.0 - 主入口"""

from database.user_db import UserDatabase
from engine import CustomerServiceEngine
from web.interface import create_web_interface
import os
import sys

print("=" * 50)
print("环境变量诊断")
print("=" * 50)

# 检查所有包含 API 关键词的环境变量
api_keys = {k: v for k, v in os.environ.items() if 'API' in k.upper() or 'KEY' in k.upper()}
print(f"找到的 API 相关变量: {list(api_keys.keys())}")

# 专门检查 DASHSCOPE
dash_key = os.getenv("DASHSCOPE_API_KEY")
print(f"DASHSCOPE_API_KEY: {'已设置 (长度: ' + str(len(dash_key)) + ')' if dash_key else '❌ 未设置'}")

# 也检查小写版本
dash_key_lower = os.getenv("dashscope_api_key")
print(f"dashscope_api_key: {'已设置' if dash_key_lower else '❌ 未设置'}")

print("=" * 50)
print()

# 如果没有读到，尝试从文件读取（备用方案）
if not dash_key:
    key_file = "api_key.txt"
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            os.environ['DASHSCOPE_API_KEY'] = f.read().strip()
        print("✅ 从 api_key.txt 读取 API Key")

def main():
    print("""
             游戏客服AI系统 v6.0 - 高性能优化版                          
             模块化架构 | 模糊意图识别 | 混合模型调度 | 响应缓存               
    """)

    EXCEL_PATH = r"G:\原G盘\大四\Autoserver\.venv\main5\data_2026.2.10.xlsx"

    try:
        print("📂 初始化数据库...")
        user_db = UserDatabase()

        print("🤖 初始化客服引擎...")
        engine = CustomerServiceEngine(EXCEL_PATH)

        print("🌐 创建Web界面...")
        demo = create_web_interface(engine, user_db)

        if demo:
            print("\n" + "=" * 50)
            print("🚀 启动成功！")
            print("   本地访问: http://127.0.0.1:7860")
            print("=" * 50)
            demo.launch(share=True, server_name="127.0.0.1", server_port=7860)
        else:
            print("❌ Web界面创建失败")

    except KeyboardInterrupt:
        print("\n\n👋 已退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()