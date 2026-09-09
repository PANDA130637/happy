"""配置管理：从 .env 读取 DeepSeek 相关配置。"""
import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "6"))


def check_api_key():
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("sk-xxxx") or DEEPSEEK_API_KEY == "sk-":
        raise RuntimeError(
            "未检测到有效的 DEEPSEEK_API_KEY。\n"
            "请复制 .env.example 为 .env，并把 DEEPSEEK_API_KEY 改成你自己的 key。"
        )