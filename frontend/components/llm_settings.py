"""
LLM 设置下拉菜单 — 允许用户在 UI 中输入模型提供方凭据。

在顶部导航中渲染，因此所有页面均可访问。配置仅保存在当前浏览器会话中
（st.session_state），不会写入磁盘或代码仓库。具体的配置解析与客户端
构建逻辑请见 utils/llm_runtime.py。
"""

import streamlit as st

from utils.llm_runtime import (
    LLM_PROVIDERS,
    clear_llm_config,
    env_api_key,
    get_llm_config,
    is_session_override,
    mask_key,
    save_llm_config,
    test_llm_connection,
)


def _status_line() -> str:
    cfg = get_llm_config()
    spec = LLM_PROVIDERS[cfg["provider"]]
    source = "浏览器会话" if is_session_override() else ".env 配置文件"
    parts = [f"**{spec['label']}**", f"`{cfg['model']}`"]
    if spec["key"]:
        parts.append(f"密钥 `{mask_key(cfg['api_key']) or '未设置'}`")
    if cfg["base_url"]:
        parts.append(f"`{cfg['base_url']}`")
    return f"当前生效：{' · '.join(parts)}  \n来源：`{source}`"


def _resolve_key(provider_id: str, typed_key: str) -> str:
    """选择提供方时的最终有效密钥：输入值优先 → 会话中已保存 → .env 文件。"""
    if typed_key.strip():
        return typed_key.strip()
    active = get_llm_config()
    if is_session_override() and active["provider"] == provider_id:
        return active["api_key"]
    return env_api_key(provider_id)


def _bump_form_version():
    """旋转 widget key 后缀，让表单根据当前配置重新构建默认值。

    折叠的 popover 内部 widget 不会在服务端被实例化，
    删除 session_state 无法覆盖客户端缓存的表单值，
    所以通过递增版本号强制重建所有 widget。
    """
    st.session_state.llm_cfg_version = st.session_state.get("llm_cfg_version", 0) + 1


def render_llm_settings():
    """渲染顶部行的 LLM 设置（API 密钥输入）弹窗。"""
    version = st.session_state.get("llm_cfg_version", 0)
    suffix = f"v{version}"
    current = get_llm_config()

    with st.popover("⚙️", use_container_width=True):
        st.markdown("### 模型 (LLM) 设置")
        st.markdown(_status_line())
        st.caption(
            "密钥仅保存在此浏览器会话中，不会写入磁盘；留空将自动使用 .env 中已配置的密钥。"
        )

        provider_labels = {pid: spec["label"] for pid, spec in LLM_PROVIDERS.items()}
        provider_id = st.selectbox(
            "提供方",
            options=list(LLM_PROVIDERS),
            format_func=lambda pid: provider_labels[pid],
            index=list(LLM_PROVIDERS).index(current["provider"]),
            key=f"llm_provider_{suffix}",
        )
        spec = LLM_PROVIDERS[provider_id]

        # 若当前会话配置属于同一个提供方，沿用其中的 base_url / model；
        # 否则使用提供方默认值。
        if is_session_override() and current["provider"] == provider_id:
            base_prefill = current["base_url"] or spec["default_url"]
            model_prefill = current["model"] or spec["default_model"]
        else:
            base_prefill = spec["default_url"]
            model_prefill = spec["default_model"]

        # widget key 由 (provider + version) 组成，切换提供方或保存/重置时会重建字段
        api_key = ""
        if spec["key"]:
            env_key = env_api_key(provider_id)
            has_session_key = (
                is_session_override()
                and current["provider"] == provider_id
                and bool(current["api_key"])
            )
            placeholder = (
                "使用当前会话中已输入的密钥"
                if has_session_key
                else ("已从 .env 读取，留空即可复用" if env_key else spec["key_hint"])
            )
            api_key = st.text_input(
                "API 密钥",
                value="",
                type="password",
                placeholder=placeholder,
                key=f"llm_api_key_{provider_id}_{suffix}",
                help=spec["key_hint"],
            )
            if env_key:
                st.caption(f"留空时将使用 .env 中已存在的密钥 (`{mask_key(env_key)}`)。")

        base_url = st.text_input(
            "基础网址 (Base URL)",
            value=base_prefill,
            placeholder=spec["url_hint"] or "使用提供方默认地址",
            key=f"llm_base_url_{provider_id}_{suffix}",
            help=spec["url_hint"] or None,
        )

        model = st.text_input(
            "模型名",
            value=model_prefill,
            key=f"llm_model_{provider_id}_{suffix}",
        )

        col_save, col_reset, col_test = st.columns([2, 2, 1.6])
        with col_save:
            if st.button("保存并应用", type="primary", use_container_width=True):
                effective_key = _resolve_key(provider_id, api_key)
                candidate = {
                    "provider": provider_id,
                    "api_key": effective_key,
                    "base_url": base_url.strip() or spec["default_url"],
                    "model": model.strip() or spec["default_model"],
                }
                if spec["key"] and not candidate["api_key"]:
                    st.error("该提供方需要填写 API 密钥。")
                else:
                    save_llm_config(provider_id, candidate["api_key"], candidate["base_url"], candidate["model"])
                    _bump_form_version()
                    st.toast("已保存 LLM 配置（仅当前浏览器会话生效）。")
                    st.rerun()
        with col_reset:
            if st.button("使用 .env 配置", use_container_width=True):
                clear_llm_config()
                _bump_form_version()
                st.toast("已恢复为 .env 配置文件中的设置。")
                st.rerun()
        with col_test:
            if st.button("测试连接", use_container_width=True):
                candidate = {
                    "provider": provider_id,
                    "api_key": _resolve_key(provider_id, api_key),
                    "base_url": base_url.strip() or spec["default_url"],
                    "model": model.strip() or spec["default_model"],
                }
                if spec["key"] and not candidate["api_key"]:
                    st.error("请先填写 API 密钥再测试。")
                else:
                    with st.spinner("正在测试连接……"):
                        ok, message = test_llm_connection(candidate)
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)
