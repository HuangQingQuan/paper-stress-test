"""
app.py — Streamlit 审稿助手主界面
运行：streamlit run app.py
"""

import streamlit as st
from paper_reader import PaperReader
from reviewer import ReviewSession, QUICK_PROMPTS

# ──────────────────────────────────────────────
# 页面配置
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="论文审稿助手",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.loli.net/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Noto Serif SC', serif; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; }

/* 顶部 */
.app-header {
    border-top: 3px solid #1a1a1a;
    padding: 1rem 0 0.8rem;
    margin-bottom: 1.5rem;
}
.app-header h1 {
    font-size: 1.3rem; font-weight: 700;
    letter-spacing: 0.04em; margin: 0 0 0.25rem;
}
.app-header p {
    font-size: 0.75rem; color: #999;
    font-family: 'JetBrains Mono', monospace; margin: 0;
}

/* 聊天消息 */
.msg-user {
    background: #f7f4ef;
    border-left: 3px solid #1a1a1a;
    padding: 0.9rem 1.1rem;
    margin: 0.8rem 0;
    font-size: 0.92rem;
    line-height: 1.75;
}
.msg-ai {
    background: white;
    border: 1px solid #e8e4de;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
    font-size: 0.92rem;
    line-height: 1.8;
}
.msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #bbb;
    margin-bottom: 0.4rem;
}

/* 快捷按钮 */
.quick-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #aaa;
    margin: 1.2rem 0 0.5rem;
}

/* 论文信息卡 */
.paper-card {
    background: #f0ede8;
    padding: 0.8rem 1rem;
    font-size: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
    color: #666;
    margin-bottom: 1rem;
    border-left: 3px solid #1a1a1a;
}
.paper-card strong { color: #1a1a1a; }

/* 侧栏 */
section[data-testid="stSidebar"] > div:first-child {
    padding: 1.5rem 1rem;
    background: #fafaf8;
}

/* 输入框底部 */
.stChatInput { border-top: 1px solid #e5e5e5; padding-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Session State 初始化
# ──────────────────────────────────────────────

def init_state():
    defaults = {
        "session":       None,    # ReviewSession
        "chat_history":  [],      # [{role, content}]
        "paper_stats":   None,
        "paper_name":    "",
        "paper_loaded":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ──────────────────────────────────────────────
# 侧栏：论文上传 + 快捷追问
# ──────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="border-top:3px solid #1a1a1a;padding-top:1rem;margin-bottom:1.2rem;">
        <div style="font-size:1.1rem;font-weight:700;">📄 论文审稿助手</div>
        <div style="font-size:0.72rem;color:#999;font-family:'JetBrains Mono',monospace;margin-top:4px;">
            顶刊审稿人视角 · 深度分析 · 改写建议
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("上传论文 PDF", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        file_key = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("_last_file") != file_key:
            with st.spinner("正在解析论文..."):
                reader = PaperReader(uploaded.read())
                context = reader.get_context_for_review()
                stats   = reader.summary_stats()
                session = ReviewSession(context)

            st.session_state["session"]      = session
            st.session_state["paper_stats"]  = stats
            st.session_state["paper_name"]   = uploaded.name
            st.session_state["paper_loaded"] = True
            st.session_state["chat_history"] = []
            st.session_state["_last_file"]   = file_key
            st.rerun()

    # 论文信息
    if st.session_state["paper_loaded"]:
        stats = st.session_state["paper_stats"]
        secs  = "、".join(stats.get("sections", [])) or "—"
        st.markdown(f"""
        <div class="paper-card">
            <strong>{st.session_state['paper_name']}</strong><br>
            {stats['pages']} 页 · {stats['chars']:,} 字符<br>
            识别章节：{secs}
        </div>
        """, unsafe_allow_html=True)

        # 快捷追问
        st.markdown('<div class="quick-label">快捷追问</div>', unsafe_allow_html=True)
        for qp in QUICK_PROMPTS:
            if st.button(qp["label"], key=f"qp_{qp['label']}", use_container_width=True,
                         help=qp["desc"]):
                st.session_state["_pending_prompt"] = qp["prompt"]
                st.rerun()

        st.divider()
        if st.button("🗑️ 清空对话记录", use_container_width=True):
            st.session_state["chat_history"] = []
            st.session_state["session"].clear_history()
            st.rerun()

    else:
        st.markdown("""
        <div style="color:#bbb;font-size:0.82rem;padding:1rem 0;line-height:1.8;">
            上传 PDF 后，你可以：<br>
            · 请AI做完整深度初审<br>
            · 追问某个具体问题<br>
            · 要求改写某段文字<br>
            · 询问适合投哪本期刊
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 主区域：对话界面
# ──────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>论文审稿助手</h1>
    <p>上传论文 · 深度审稿 · 追问改写 · 直到满意</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state["paper_loaded"]:
    st.markdown("""
    <div style="text-align:center;padding:5rem 2rem;color:#ccc;border:2px dashed #e5e5e5;">
        <div style="font-size:2rem;margin-bottom:1rem;">📄</div>
        <div style="font-size:1rem;color:#aaa;">在左侧上传论文 PDF 开始审稿</div>
        <div style="font-size:0.8rem;margin-top:0.5rem;">支持中英文 · 文件不会被保存</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 渲染历史对话
for msg in st.session_state["chat_history"]:
    if msg["role"] == "user":
        st.markdown(f"""
        <div class="msg-user">
            <div class="msg-label">你</div>
            {msg["content"].replace(chr(10), "<br>")}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-ai">
            <div class="msg-label">审稿人</div>
        """, unsafe_allow_html=True)
        st.markdown(msg["content"])
        st.markdown("</div>", unsafe_allow_html=True)

# 处理待发送的消息（来自快捷按钮或输入框）
pending = st.session_state.pop("_pending_prompt", None)
user_input = st.chat_input("向审稿人提问，或要求改写某段文字…")
prompt = pending or user_input

if prompt:
    session: ReviewSession = st.session_state["session"]

    # 显示用户消息
    st.markdown(f"""
    <div class="msg-user">
        <div class="msg-label">你</div>
        {prompt.replace(chr(10), "<br>")}
    </div>
    """, unsafe_allow_html=True)

    # 流式输出AI回复
    st.markdown("""
    <div class="msg-ai">
        <div class="msg-label">审稿人</div>
    """, unsafe_allow_html=True)

    response_container = st.empty()
    full_response = ""

    for delta in session.chat(prompt):
        full_response += delta
        response_container.markdown(full_response + "▌")

    response_container.markdown(full_response)
    st.markdown("</div>", unsafe_allow_html=True)

    # 存入历史
    st.session_state["chat_history"].append({"role": "user",    "content": prompt})
    st.session_state["chat_history"].append({"role": "assistant","content": full_response})
    st.rerun()
