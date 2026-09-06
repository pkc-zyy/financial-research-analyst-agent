"""
前端 LLM 运行时 —— 负责解析当前生效的模型提供方与凭据。

使用优先级（前端实际调用哪一个模型的唯一依据）：
1. 会话级覆盖 —— 用户在应用内的"模型设置"面板里输入的配置
   （仅存入 st.session_state，不会写入磁盘）
2. 环境/配置文件 —— src/config.py 从 .env 读取的全局 settings

提供方注册表结构通用：只要新增一条注册表项（一行）即可接入
任意 OpenAI 兼容的模型厂商。
"""

import streamlit as st

# ─── 提供方注册表 ─────────────────────────────────────────
# kind:    构建哪种 LangChain 客户端（"openai" 可覆盖所有 OpenAI 兼容端点）
# key:     是否需要 API key
# default_model / default_url: 下拉时的默认值，用户可在 UI 中修改

LLM_PROVIDERS = {
    "openai": {
        "label": "OpenAI",
        "kind": "openai",
        "key": True,
        "default_model": "gpt-4o-mini",
        "default_url": "",
        "url_hint": "可选 —— 用于 OpenRouter、DeepSeek 等兼容网关",
        "key_hint": "形如 sk-…，在 platform.openai.com 获取",
    },
    "dashscope": {
        "label": "阿里云百炼 DashScope (通义千问 Qwen)",
        "kind": "openai",
        "key": True,
        "default_model": "qwen-plus",
        "default_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "url_hint": "DashScope OpenAI 兼容接口地址",
        "key_hint": "形如 sk-…，在 bailian.console.aliyun.com 获取",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "kind": "anthropic",
        "key": True,
        "default_model": "claude-sonnet-4-5",
        "default_url": "",
        "url_hint": "",
        "key_hint": "形如 sk-ant-…，在 console.anthropic.com 获取",
    },
    "groq": {
        "label": "Groq (高速推理)",
        "kind": "groq",
        "key": True,
        "default_model": "llama-3.3-70b-versatile",
        "default_url": "",
        "url_hint": "",
        "key_hint": "形如 gsk_…，在 console.groq.com 获取",
    },
    "ollama": {
        "label": "Ollama (本地)",
        "kind": "ollama",
        "key": False,
        "default_model": "llama4:latest",
        "default_url": "http://localhost:11434",
        "url_hint": "Ollama 本地服务地址",
        "key_hint": "",
    },
    "lmstudio": {
        "label": "LM Studio (本地)",
        "kind": "openai",
        "key": False,
        "default_model": "local-model",
        "default_url": "http://localhost:1234/v1",
        "url_hint": "LM Studio 本地服务地址",
        "key_hint": "",
    },
    "vllm": {
        "label": "vLLM (自部署)",
        "kind": "openai",
        "key": False,
        "default_model": "meta-llama/Llama-3.2-8B-Instruct",
        "default_url": "http://localhost:8000/v1",
        "url_hint": "vLLM 服务地址",
        "key_hint": "",
    },
}

_SESSION_KEY = "llm_config_override"


# ─── 配置解析 ─────────────────────────────────────────────────


def _config_from_env() -> dict:
    """根据 .env 载入的 settings 构造标准化配置字典。"""
    from src.config import settings

    llm = settings.llm
    provider = llm.provider.lower()

    if provider == "openai":
        provider_id = "dashscope" if "dashscope" in llm.base_url else "openai"
        return {
            "provider": provider_id,
            "api_key": llm.openai_api_key,
            "base_url": llm.base_url,
            "model": llm.model if llm.model != "llama4:latest" else "gpt-4o-mini",
        }
    if provider == "anthropic":
        return {
            "provider": "anthropic",
            "api_key": llm.anthropic_api_key,
            "base_url": "",
            "model": llm.model if llm.model != "llama4:latest" else "claude-sonnet-4-5",
        }
    if provider == "groq":
        return {
            "provider": "groq",
            "api_key": llm.groq_api_key,
            "base_url": "",
            "model": llm.groq_model,
        }
    if provider == "lmstudio":
        return {
            "provider": "lmstudio",
            "api_key": "",
            "base_url": llm.lmstudio_base_url,
            "model": llm.lmstudio_model,
        }
    if provider == "vllm":
        return {
            "provider": "vllm",
            "api_key": "",
            "base_url": llm.vllm_base_url,
            "model": llm.vllm_model,
        }
    # ollama 或其它未识别情况回退到 ollama
    return {
        "provider": "ollama",
        "api_key": "",
        "base_url": llm.ollama_base_url,
        "model": llm.ollama_model,
    }


def get_llm_config() -> dict:
    """获取最终生效的 LLM 配置（会话优先，否则 .env）。"""
    override = st.session_state.get(_SESSION_KEY)
    if override:
        return dict(override)
    return _config_from_env()


def is_session_override() -> bool:
    """当前配置来自 UI 输入（而非 .env 文件）则返回 True。"""
    return bool(st.session_state.get(_SESSION_KEY))


def save_llm_config(provider_id: str, api_key: str, base_url: str, model: str):
    """仅在当前浏览器会话中保存 UI 中输入的配置。"""
    spec = LLM_PROVIDERS[provider_id]
    st.session_state[_SESSION_KEY] = {
        "provider": provider_id,
        "api_key": (api_key or "").strip(),
        "base_url": (base_url or "").strip() or spec["default_url"],
        "model": (model or "").strip() or spec["default_model"],
    }


def clear_llm_config():
    """清除会话级覆盖配置，回退为 .env 文件中的配置。"""
    st.session_state.pop(_SESSION_KEY, None)


def env_api_key(provider_id: str) -> str:
    """读取 .env 中为某个提供方配置的 API key（可能为空字符串）。"""
    from src.config import settings

    llm = settings.llm
    return {
        "openai": llm.openai_api_key,
        "dashscope": llm.openai_api_key,
        "anthropic": llm.anthropic_api_key,
        "groq": llm.groq_api_key,
    }.get(provider_id, "")


def mask_key(key: str) -> str:
    """把 API key 脱敏后展示（保留前后几位，中间打星号）。"""
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "****"
    return f"{key[:5]}****{key[-4:]}"


# ─── 模型实例工厂 ─────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _build_llm(provider_id: str, api_key: str, base_url: str, model: str, temperature: float):
    """根据参数构造 LangChain 聊天模型实例。

    按 (provider, api_key, base_url, model, temperature) 元组缓存，
    因此在 UI 中重新保存新凭据后会自动得到一个新的客户端。
    """
    kind = LLM_PROVIDERS[provider_id]["kind"]

    if kind == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key or "not-set",
            base_url=base_url or None,
        )
    if kind == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=api_key or "not-set",
            max_tokens=4096,
        )
    if kind == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            temperature=temperature,
            api_key=api_key or "not-set",
        )
    # ollama
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model,
        base_url=base_url or "http://localhost:11434",
        temperature=temperature,
    )


def get_llm(temperature: float = 0.7):
    """根据当前生效配置返回 LangChain ChatModel 实例。"""
    cfg = get_llm_config()
    return _build_llm(
        cfg["provider"], cfg["api_key"], cfg["base_url"], cfg["model"], temperature
    )


def test_llm_connection(cfg: dict = None) -> tuple[bool, str]:
    """发一条极简 prompt 验证连接是否正常。返回 (是否成功, 消息)。"""
    try:
        llm = _build_llm(
            cfg["provider"],
            cfg["api_key"],
            cfg["base_url"],
            cfg["model"],
            0.0,
        )
        reply = llm.invoke("Reply with exactly: OK")
        text = (reply.content or "").strip()
        return True, f"连接成功 —— 模型回复：{text[:80] or '(空)'}"
    except Exception as e:
        return False, str(e)[:300]
