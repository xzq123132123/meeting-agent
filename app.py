# -*- coding: utf-8 -*-
"""
智能会议纪要 & 周报 Agent
多模态输入（文本 / 文件）→ 结构化纪要 → 可视化周报 → Word 导出
"""
import os
import sys
import hashlib
import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import llm, parser, prompts, report, export, asr
from sample_data import (
    SAMPLE_MEETING_1, SAMPLE_MEETING_2,
    SAMPLE_MEETING_1_RESULT, SAMPLE_MEETING_2_RESULT,
    SAMPLE_WEEKLY_RESULT, SAMPLE_AUDIO_TRANSCRIPT,
    SAMPLE_QA_REPLIES,
)

# 模型服务商预设（OpenAI 兼容接口）
PROVIDERS = {
    "通义千问（阿里云百炼）": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_hint": "如 qwen-plus / qwen-turbo / qwen-max",
    },
    "豆包方舟（火山引擎）": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model_hint": "控制台开通后查 Model ID，如 doubao-seed-1-6-251015",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com",
        "model_hint": "如 deepseek-chat / deepseek-reasoner",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model_hint": "如 gpt-4o-mini",
    },
    "智谱 GLM": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model_hint": "如 glm-4-flash",
    },
    "自定义": {
        "base_url": "",
        "model_hint": "任意 OpenAI 兼容接口",
    },
}

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="智纪 · 会议纪要 & 周报 Agent",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 全局样式
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
/* ===== 全局 ===== */
.stApp {
    background:
        radial-gradient(1200px 600px at 15% -10%, rgba(94,169,240,0.18), transparent 60%),
        radial-gradient(900px 500px at 95% 5%, rgba(124,124,255,0.14), transparent 55%),
        linear-gradient(180deg, #0B1220 0%, #0E1626 100%);
}
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1200px; }
#MainMenu, footer { visibility: hidden; }

/* ===== 标题 ===== */
.hero-title {
    font-size: 42px; font-weight: 800; line-height: 1.15; letter-spacing: 1px;
    background: linear-gradient(92deg, #7CC0FF 0%, #9F8CFF 55%, #6FE3C1 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 6px 0;
}
.hero-sub { color: #8AA0BC; font-size: 15px; margin: 0 0 6px 0; }
.hero-badge {
    display: inline-block; font-size: 12px; font-weight: 600; color: #BFE3FF;
    background: rgba(94,169,240,0.14); border: 1px solid rgba(94,169,240,0.35);
    padding: 3px 12px; border-radius: 999px; margin-bottom: 10px; letter-spacing: 2px;
}

/* ===== 卡片 ===== */
.glass-card {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 18px 20px;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.25);
}
.section-title {
    font-size: 15px; font-weight: 700; color: #E8EEF7;
    letter-spacing: 1.5px; margin: 4px 0 12px 0;
    display: flex; align-items: center; gap: 8px;
}
.section-title::before {
    content: ""; display: inline-block; width: 4px; height: 16px;
    border-radius: 2px; background: linear-gradient(180deg, #7CC0FF, #9F8CFF);
}

/* ===== 步骤条 ===== */
.steps { display: flex; gap: 0; align-items: center; flex-wrap: wrap; margin: 4px 0 16px 0; }
.step { display: flex; align-items: center; gap: 10px; }
.step-dot {
    width: 34px; height: 34px; border-radius: 50%; flex: 0 0 auto;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700; color: #0B1220;
    background: linear-gradient(135deg, #7CC0FF, #9F8CFF);
    box-shadow: 0 0 18px rgba(124,192,255,0.45);
}
.step-label { font-size: 13px; color: #AEC3DD; white-space: nowrap; }
.step-line { width: 52px; height: 2px; margin: 0 10px; background: linear-gradient(90deg, rgba(124,192,255,0.7), rgba(255,255,255,0.12)); }

/* ===== 指标卡 ===== */
.metric-card {
    background: linear-gradient(135deg, rgba(94,169,240,0.12), rgba(124,124,255,0.10));
    border: 1px solid rgba(94,169,240,0.28);
    border-radius: 14px; padding: 12px 16px; text-align: center;
}
.metric-num { font-size: 26px; font-weight: 800; color: #7CC0FF; }
.metric-label { font-size: 12px; color: #8AA0BC; margin-top: 2px; }

/* ===== 议题卡 ===== */
.topic-card {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 3px solid #7CC0FF;
    border-radius: 12px; padding: 12px 16px; margin-bottom: 10px;
}
.topic-title { font-size: 14.5px; font-weight: 700; color: #E8EEF7; margin-bottom: 6px; }
.topic-point { font-size: 13px; color: #B8C9E0; margin: 3px 0 3px 0; line-height: 1.55; }
.topic-point::before { content: "▸ "; color: #7CC0FF; }
.topic-conclusion {
    font-size: 13px; color: #9AD7C3; margin-top: 7px; line-height: 1.55;
    background: rgba(111,227,193,0.08); border-radius: 8px; padding: 6px 10px;
}
.topic-conclusion::before { content: "结论  "; font-weight: 700; color: #6FE3C1; }

/* ===== 风险/亮点 ===== */
.risk-item { font-size: 13px; color: #F3B8B8; margin: 4px 0; line-height: 1.5; }
.risk-item::before { content: "▲ "; color: #F26D6D; }
.good-item { font-size: 13px; color: #A9E6CB; margin: 4px 0; line-height: 1.5; }
.good-item::before { content: "★ "; color: #6FE3C1; }

/* ===== 摘要 ===== */
.summary-text { font-size: 14px; color: #C7D6EA; line-height: 1.7; }

/* ===== 按钮与输入 ===== */
.stButton > button {
    border-radius: 10px; font-weight: 700; border: none;
    background: linear-gradient(92deg, #4E97E8, #7B6CF0);
    color: #FFFFFF; padding: 10px 26px; transition: all .2s ease;
    box-shadow: 0 4px 18px rgba(78,151,232,0.35);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 26px rgba(123,108,240,0.45);
    color: #FFFFFF;
}
.stDownloadButton > button {
    border-radius: 10px; font-weight: 600;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.18);
    color: #D6E4F7; transition: all .2s ease;
}
.stDownloadButton > button:hover {
    border-color: #7CC0FF; color: #7CC0FF;
}
textarea, [data-testid="stFileUploaderDropzone"] {
    border-radius: 12px !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px dashed rgba(124,192,255,0.4) !important;
}
[data-testid="stSidebar"] {
    background: rgba(13,20,33,0.92);
    border-right: 1px solid rgba(255,255,255,0.06);
}

/* 表格 */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* 标签页 */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0; padding: 6px 18px; font-weight: 600; color: #8AA0BC;
}
.stTabs [aria-selected="true"] { color: #7CC0FF !important; background: rgba(94,169,240,0.10); }

/* 分隔 */
.divider {
    height: 1px; margin: 22px 0; border: none;
    background: linear-gradient(90deg, transparent, rgba(124,192,255,0.35), transparent);
}

/* 动画 */
@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
.fade-up { animation: fadeUp .45s ease both; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 会话状态
# ---------------------------------------------------------------------------
def init_state():
    if "meetings" not in st.session_state:
        st.session_state.meetings = []       # 已生成的纪要列表
    if "meeting_fps" not in st.session_state:
        st.session_state.meeting_fps = []    # 已分析内容的指纹（去重）
    if "weekly_text" not in st.session_state:
        st.session_state.weekly_text = ""
    if "weekly_meta" not in st.session_state:
        st.session_state.weekly_meta = None
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []     # 智能问答对话历史


init_state()

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def merge_meetings(blocks: list) -> dict:
    """合并多块纪要结果。"""
    topics, todos, risks, participants = [], [], [], []
    title = blocks[0].get("title", "会议纪要") if blocks else "会议纪要"
    for b in blocks:
        topics.extend(b.get("topics", []) or [])
        todos.extend(b.get("todos", []) or [])
        risks.extend(b.get("risks", []) or [])
        participants.extend(b.get("participants", []) or [])
    participants = list(dict.fromkeys(participants))
    summary = blocks[0].get("summary", "")
    if len(blocks) > 1:
        summary += f"（内容较长，已分 {len(blocks)} 段处理）"
    return {
        "title": title,
        "summary": summary,
        "topics": topics,
        "todos": todos,
        "risks": risks,
        "participants": participants,
        "duration": blocks[0].get("duration", ""),
    }


# ---- 侧边栏：配置 ----
with st.sidebar:
    st.markdown("### ⚙️ 智能体配置")
    use_sample = st.toggle(
        "示例模式（无需 API Key，离线可用）",
        value=True,
        help="开启后使用内置演示数据，适合演示与测试",
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("#### 模型接口")

    provider_names = list(PROVIDERS.keys())
    provider = st.selectbox(
        "模型服务商",
        provider_names,
        index=provider_names.index("通义千问（阿里云百炼）"),
        help="选择后自动填入对应 Base URL 与模型示例",
    )
    prov = PROVIDERS[provider]

    base_url = st.text_input(
        "API Base URL",
        value=prov["base_url"],
        key=f"base_url_{provider}",
        help="OpenAI 兼容接口地址，已按服务商自动填入，可手动修改",
    )
    api_key = st.text_input("API Key", type="password", placeholder="sk-... 或 apikey-...")
    model = st.text_input(
        "模型名称 / Endpoint ID",
        placeholder=prov["model_hint"],
        key=f"model_{provider}",
    )
    if model.strip().startswith("apikey-") or len(model.strip()) >= 30 and "-" in model.strip():
        st.warning("⚠️ 「模型名称」框里似乎填的是 API Key，请把它填到上方「API Key」框，这里填模型名（如 qwen-plus）或接入点 ID")

    with st.expander("🎙 语音转写配置", expanded=False):
        st.caption("上传语音后，用此配置把录音转成文字（复用上方 API Key）")
        asr_base = st.text_input(
            "ASR Base URL",
            value="https://dashscope.aliyuncs.com/compatible-mode/v1",
            key="asr_base",
            help="通义千问默认即可；OpenAI 等也可填对应地址",
        )
        asr_model = st.text_input(
            "ASR 模型",
            value="qwen3-asr-flash",
            key="asr_model",
            help="通义千问：qwen3-asr-flash / paraformer-v2；OpenAI：whisper-1",
        )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if st.button("清空已生成纪要", use_container_width=True):
        st.session_state.meetings = []
        st.session_state.meeting_fps = []
        st.session_state.weekly_text = ""
        st.session_state.weekly_meta = None
        st.session_state.qa_history = []
        # 一并清空输入状态（侧边栏先于主区渲染，此处安全）
        st.session_state.pop("input_file_content", None)
        st.session_state.pop("_sample_loaded", None)
        st.session_state.pop("input_text", None)

    st.markdown(
        '<div style="color:#5C7290;font-size:11px;line-height:1.6;margin-top:18px;">'
        "💡 支持：文本粘贴 / txt / md / csv / log / docx 文件<br>"
        "提示词输出严格 JSON，失败自动重试</div>",
        unsafe_allow_html=True,
    )

cfg = {
    "use_sample": use_sample,
    "base_url": base_url.strip(),
    "api_key": api_key.strip(),
    "model": model.strip(),
    "asr_base": asr_base.strip(),
    "asr_model": asr_model.strip(),
}

# ---------------------------------------------------------------------------
# 主区
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="hero-badge">AI OFFICE AGENT · 实习作品</div>'
    '<div class="hero-title">智纪 · 会议纪要 & 周报智能体</div>'
    '<div class="hero-sub">粘贴聊天记录、上传会议文档，一键生成结构化纪要、待办清单与可视化周报</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="steps">'
    '<div class="step"><div class="step-dot">1</div><div class="step-label">多模态输入</div></div>'
    '<div class="step-line"></div>'
    '<div class="step"><div class="step-dot">2</div><div class="step-label">智能分析</div></div>'
    '<div class="step-line"></div>'
    '<div class="step"><div class="step-dot">3</div><div class="step-label">纪要 · 待办</div></div>'
    '<div class="step-line"></div>'
    '<div class="step"><div class="step-dot">4</div><div class="step-label">周报 · 导出</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---- 输入区 ----
with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">① 输入会议 / 聊天内容</div>', unsafe_allow_html=True)

    tab_text, tab_file, tab_audio, tab_sample = st.tabs(
        ["📝 粘贴文本", "📁 上传文件", "🎙 上传语音", "⚡ 示例数据"]
    )

    with tab_text:
        st.text_area(
            "将会议记录、语音转写文本或聊天记录粘贴到这里",
            height=220,
            placeholder="例：项目周会纪要...\n张老师：数据采集进度如何？\n李磊：目前采集了 3200 张...",
            key="input_text",
        )
    with tab_file:
        up = st.file_uploader(
            "支持 txt / md / csv / log / docx",
            type=["txt", "md", "csv", "log", "docx"],
        )
        if up is not None:
            try:
                tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_upload_tmp")
                os.makedirs(tmp, exist_ok=True)
                path = os.path.join(tmp, up.name)
                with open(path, "wb") as f:
                    f.write(up.getbuffer())
                st.session_state["input_file_content"] = parser.read_file(path)
                st.success(f"已读取「{up.name}」，共 {len(st.session_state['input_file_content'])} 字")
            except Exception as e:
                st.error(f"文件读取失败：{e}")
    with tab_audio:
        audio_up = st.file_uploader(
            "上传会议录音（wav / mp3 / m4a / flac / ogg / aac）",
            type=["wav", "mp3", "m4a", "flac", "ogg", "aac"],
            key="audio_uploader",
        )
        btn_col, hint_col = st.columns([1, 2])
        with btn_col:
            transcribe_btn = st.button("🎙 转写为文字", key="transcribe_btn",
                                       use_container_width=True)
        with hint_col:
            st.markdown(
                '<div style="color:#6E84A3;font-size:12px;padding-top:8px;">'
                + ("示例模式：将模拟转写一段会议录音" if cfg["use_sample"]
                   else "调用语音识别模型转写，需先在侧边栏配置 API Key")
                + "</div>",
                unsafe_allow_html=True,
            )
        if transcribe_btn:
            if cfg["use_sample"]:
                st.session_state["input_file_content"] = SAMPLE_AUDIO_TRANSCRIPT
                st.success("示例模式：已模拟转写完成，点击下方「开始智能分析」即可")
            elif audio_up is None:
                st.error("请先上传音频文件")
            else:
                if not llm.is_configured(cfg["base_url"], cfg["api_key"], cfg["asr_model"]):
                    st.error("请先在侧边栏填写 API Key，并确认语音转写配置")
                else:
                    try:
                        with st.status("语音转写中…", expanded=True) as status:
                            st.write(f"▸ 正在识别「{audio_up.name}」")
                            text = asr.transcribe_audio(
                                audio_up.getbuffer().tobytes(),
                                audio_up.name,
                                cfg["asr_base"], cfg["api_key"], cfg["asr_model"],
                            )
                            status.update(label="转写完成", state="complete")
                        st.session_state["input_file_content"] = text
                        st.success(f"转写完成，共 {len(text)} 字，点击下方「开始智能分析」即可")
                        with st.expander("查看转写文本"):
                            st.write(text)
                    except asr.LLMError as e:
                        st.error(f"转写失败：{e}")
                    except Exception as e:
                        st.error(f"发生错误：{e}")
    with tab_sample:
        s1, s2 = st.columns(2)
        with s1:
            if st.button("载入示例 · 项目周会", use_container_width=True):
                st.session_state["_sample_loaded"] = SAMPLE_MEETING_1
        with s2:
            if st.button("载入示例 · 群聊记录", use_container_width=True):
                st.session_state["_sample_loaded"] = SAMPLE_MEETING_2
        loaded = st.session_state.get("_sample_loaded", "")
        if loaded:
            st.markdown(
                f'<div style="color:#6FE3C1;font-size:13px;margin-top:8px;">'
                f"✅ 已载入示例内容（{len(loaded)} 字），点击下方「开始智能分析」即可</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="color:#6E84A3;font-size:12px;margin-top:8px;">'
                "点击按钮载入示例内容，无需复制粘贴</div>",
                unsafe_allow_html=True,
            )

    # 输入归一化：优先级 = 上传文件 > 文本框输入 > 示例载入
    if st.session_state.get("input_file_content", "").strip():
        content = st.session_state["input_file_content"]
    elif st.session_state.get("input_text", "").strip():
        content = st.session_state["input_text"]
    else:
        content = st.session_state.get("_sample_loaded", "")

    st.markdown("</div>", unsafe_allow_html=True)

# ---- 分析按钮 ----
btn_c, btn_hint = st.columns([1, 3])
with btn_c:
    analyze_btn = st.button("✨ 开始智能分析", type="primary", use_container_width=True)
with btn_hint:
    if not cfg["use_sample"] and not llm.is_configured(cfg["base_url"], cfg["api_key"], cfg["model"]):
        st.markdown(
            '<div style="color:#E8C05A;font-size:13px;padding-top:10px;">⚠️ 请先在左侧填写 API 配置，'
            "或开启示例模式</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:#6E84A3;font-size:13px;padding-top:10px;">'
            + ("离线示例模式 · 即时出结果" if cfg["use_sample"] else "实时调用大模型 · 长文本自动分段")
            + "</div>",
            unsafe_allow_html=True,
        )

if analyze_btn:
    if not content.strip():
        st.error("请先输入内容或选择示例数据")
    else:
        # 去重：同一内容只分析一次，避免重复追加相同纪要
        content_fp = hashlib.md5(content.strip().encode("utf-8")).hexdigest()
        if content_fp in st.session_state.meeting_fps:
            st.warning("当前内容已分析过，结果已在下方展示。可载入另一份内容（如群聊示例）生成新纪要，或先清空已生成纪要。")
        elif cfg["use_sample"]:
            # 示例模式：按内容匹配内置结果（含"群聊"或与示例2相同则用示例2）
            if "群聊" in content or content.strip() == SAMPLE_MEETING_2.strip():
                st.session_state.meetings.append(SAMPLE_MEETING_2_RESULT)
            else:
                st.session_state.meetings.append(SAMPLE_MEETING_1_RESULT)
            st.session_state.meeting_fps.append(content_fp)
            st.toast("示例分析完成 ✅")
        else:
            if not llm.is_configured(cfg["base_url"], cfg["api_key"], cfg["model"]):
                st.error("请先在侧边栏填写 API 配置（Base URL / Key / 模型名）")
            else:
                try:
                    meeting = call_meeting_llm(content, cfg)
                    st.session_state.meetings.append(meeting)
                    st.session_state.meeting_fps.append(content_fp)
                    st.toast("分析完成 ✅")
                except llm.LLMError as e:
                    st.error(f"分析失败：{e}")
                except Exception as e:
                    st.error(f"发生错误：{e}")

# ---- 结果区 ----
if st.session_state.meetings:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="font-size:17px;">📋 纪要结果（按生成顺序）</div>',
                unsafe_allow_html=True)

    for idx, m in enumerate(st.session_state.meetings):
        render_meeting_card(idx, m)

    render_weekly_section(cfg)
    render_qa_section(cfg)
else:
    st.markdown(
        '<div style="text-align:center;color:#5C7290;font-size:14px;padding:48px 0;">'
        "👆 输入内容后点击「开始智能分析」，纪要结果将展示在这里</div>",
        unsafe_allow_html=True,
    )
