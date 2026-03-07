"""
app.py — Streamlit 主界面
运行方式：streamlit run app.py
"""

import streamlit as st
from engine import PaperEngine
from ai_advisor import get_ai_questions, AI_SUPPORTED_IDS

# ──────────────────────────────────────────────
# 页面配置
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="论文压力测试",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.loli.net/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Serif SC', serif;
}

/* 隐藏默认streamlit元素 */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 960px; }

/* 顶部标题区 */
.pst-header {
    border-top: 3px solid #1a1a1a;
    border-bottom: 1px solid #ddd;
    padding: 1.5rem 0 1.2rem;
    margin-bottom: 2rem;
}
.pst-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin: 0 0 0.3rem 0;
    color: #1a1a1a;
}
.pst-header p {
    font-size: 0.82rem;
    color: #888;
    font-family: 'JetBrains Mono', monospace;
    margin: 0;
}

/* 得分卡 */
.score-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 2rem;
}
.score-card {
    background: white;
    border: 1px solid #e5e5e5;
    padding: 1rem 1.2rem;
}
.score-card .sc-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #999;
    margin-bottom: 0.3rem;
}
.score-card .sc-num {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1;
    color: #1a1a1a;
}
.score-card .sc-num.bad  { color: #c0392b; }
.score-card .sc-num.warn { color: #d35400; }
.score-card .sc-num.good { color: #27ae60; }
.score-card .sc-denom { font-size: 1.1rem; color: #ccc; font-weight: 400; }
.score-card .sc-sub {
    font-size: 0.75rem;
    color: #bbb;
    margin-top: 0.2rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Section heading */
.sec-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #999;
    border-bottom: 1px solid #e5e5e5;
    padding-bottom: 0.5rem;
    margin: 2.5rem 0 1.2rem;
}

/* 结构检查行 */
.struct-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 0.7rem 0;
    border-bottom: 1px solid #f0ede8;
    font-size: 0.9rem;
}
.struct-row:last-child { border-bottom: none; }
.cat-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    background: #f0ede8;
    color: #888;
    padding: 2px 7px;
    white-space: nowrap;
    margin-top: 2px;
}
.struct-name { flex: 1; color: #333; }
.ok-dot  { color: #27ae60; font-size: 1.1rem; }
.err-dot { color: #c0392b; font-size: 1.1rem; }
.evidence-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #aaa;
    margin-top: 3px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 500px;
}

/* 方法追问卡 */
.mcard {
    border-left: 4px solid #e5e5e5;
    background: #fafafa;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
.mcard.high   { border-left-color: #c0392b; background: #fdf2f0; }
.mcard.medium { border-left-color: #d35400; background: #fdf6ef; }
.mcard.passed { border-left-color: #27ae60; background: #f0faf4; }

.mcard-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 0.5rem;
}
.mcard-title { font-weight: 700; font-size: 0.95rem; color: #1a1a1a; }
.risk-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 2px 8px;
    color: white;
}
.risk-chip.high   { background: #c0392b; }
.risk-chip.medium { background: #d35400; }
.risk-chip.passed { background: #27ae60; }

.block-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #aaa;
    margin: 0.8rem 0 0.3rem;
}
.why-text  { font-size: 0.85rem; color: #555; line-height: 1.7; }
.how-item  {
    font-size: 0.83rem;
    color: #444;
    padding: 0.35rem 0 0.35rem 1.2rem;
    border-bottom: 1px dashed #e8e4de;
    position: relative;
    line-height: 1.6;
}
.how-item:last-child { border-bottom: none; }
.how-item::before {
    content: "→";
    position: absolute;
    left: 0;
    color: #ccc;
    font-family: 'JetBrains Mono', monospace;
}

/* AI追问区块 */
.ai-questions {
    background: white;
    border: 1px solid #e0dbd2;
    padding: 0.8rem 1rem;
    margin-top: 0.6rem;
}
.ai-q-item {
    font-size: 0.85rem;
    color: #2c3e50;
    padding: 0.4rem 0;
    border-bottom: 1px solid #f0ede8;
    padding-left: 1.2rem;
    position: relative;
}
.ai-q-item:last-child { border-bottom: none; }
.ai-q-item::before {
    content: "？";
    position: absolute;
    left: 0;
    color: #c0392b;
    font-weight: 700;
    font-size: 0.8rem;
}

/* 方法标签 */
.method-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    background: #1a1a1a;
    color: white;
    padding: 3px 10px;
    margin-bottom: 1rem;
}

/* 上传区域美化 */
.upload-hint {
    text-align: center;
    padding: 3rem 2rem;
    border: 2px dashed #ddd;
    color: #aaa;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def score_color(bad, total):
    if total == 0: return "good"
    r = bad / total
    if r == 0: return "good"
    if r <= 0.33: return "warn"
    return "bad"


def render_score_row(struct, did_results, iv_results):
    s_bad = sum(1 for r in struct if not r["passed"])
    s_ok  = len(struct) - s_bad
    m_all = did_results + iv_results
    m_bad = sum(1 for r in m_all if not r["passed"])
    m_ok  = len(m_all) - m_bad

    sc = score_color(s_bad, len(struct))
    mc = score_color(m_bad, len(m_all)) if m_all else "good"

    method_html = f"""
    <div class="score-card">
        <div class="sc-label">方法通过</div>
        <div class="sc-num {mc}">{m_ok}<span class="sc-denom">/{len(m_all)}</span></div>
        <div class="sc-sub">项已覆盖</div>
    </div>
    <div class="score-card">
        <div class="sc-label">方法风险</div>
        <div class="sc-num {'bad' if m_bad > 0 else 'good'}">{m_bad}<span class="sc-denom">/{len(m_all)}</span></div>
        <div class="sc-sub">项需关注</div>
    </div>
    """ if m_all else ""

    html = f"""
    <div class="score-grid">
        <div class="score-card">
            <div class="sc-label">结构通过</div>
            <div class="sc-num {sc}">{s_ok}<span class="sc-denom">/{len(struct)}</span></div>
            <div class="sc-sub">项已检测到</div>
        </div>
        <div class="score-card">
            <div class="sc-label">结构缺失</div>
            <div class="sc-num {'bad' if s_bad > 0 else 'good'}">{s_bad}<span class="sc-denom">/{len(struct)}</span></div>
            <div class="sc-sub">项建议补充</div>
        </div>
        {method_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_structure(struct):
    st.markdown('<div class="sec-title">第一层 · 结构完整性检查</div>', unsafe_allow_html=True)
    rows_html = ""
    for r in struct:
        dot = '<span class="ok-dot">✓</span>' if r["passed"] else '<span class="err-dot">✗</span>'
        ev = ""
        if r["passed"] and r["evidence"]:
            ev = f'<div class="evidence-text">{r["evidence"][:80]}</div>'
        elif not r["passed"]:
            ev = f'<div style="font-size:0.75rem;color:#c0392b;margin-top:3px;">{r["evidence"]}</div>'
        rows_html += f"""
        <div class="struct-row">
            <span class="cat-tag">{r['category']}</span>
            <div class="struct-name">{r['name']}{ev}</div>
            {dot}
        </div>"""
    st.markdown(rows_html, unsafe_allow_html=True)


def render_method_cards(cards: list[dict], method_key: str, excerpt: str):
    """渲染一组方法追问卡，支持展开修复路径和AI逻辑追问"""
    for card in cards:
        cid = card["id"]
        passed = card["passed"]
        risk = card["risk"] if not passed else "passed"
        risk_label = {"high": "高风险", "medium": "中风险", "passed": "通过"}.get(risk, risk)

        card_class = risk if not passed else "passed"

        card_html = f"""
        <div class="mcard {card_class}">
            <div class="mcard-head">
                <span class="mcard-title">{card['title']}</span>
                <span class="risk-chip {card_class}">{risk_label}</span>
            </div>
        """
        if passed:
            card_html += '<div style="font-size:0.82rem;color:#27ae60;">✓ 已在文中检测到相关内容</div>'
        else:
            card_html += f'<div style="font-size:0.85rem;color:#c0392b;margin-bottom:0.5rem;">{card["question"]}</div>'
        card_html += "</div>"
        st.markdown(card_html, unsafe_allow_html=True)

        if not passed:
            col1, col2 = st.columns([1, 1])

            # 修复路径
            with col1:
                fix_key = f"fix_{method_key}_{cid}"
                if st.button("📋 查看修复路径", key=fix_key, use_container_width=True):
                    st.session_state[f"show_fix_{cid}"] = not st.session_state.get(f"show_fix_{cid}", False)

            # AI追问（仅支持的项显示）
            with col2:
                if cid in AI_SUPPORTED_IDS:
                    ai_key = f"ai_{method_key}_{cid}"
                    if st.button("🤖 AI逻辑追问", key=ai_key, use_container_width=True):
                        st.session_state[f"show_ai_{cid}"] = True
                        if f"ai_q_{cid}" not in st.session_state:
                            with st.spinner("正在生成针对本文的追问..."):
                                qs = get_ai_questions(cid, excerpt)
                                st.session_state[f"ai_q_{cid}"] = qs

            # 展示修复路径
            if st.session_state.get(f"show_fix_{cid}", False):
                items_html = "".join(f'<div class="how-item">{h}</div>' for h in card["how"])
                st.markdown(f"""
                <div style="margin:-0.3rem 0 0.8rem;padding:0.8rem 1rem;background:white;border:1px solid #e0dbd2;">
                    <div class="block-label">为何重要</div>
                    <div class="why-text">{card['why']}</div>
                    <div class="block-label">修复路径</div>
                    {items_html}
                </div>""", unsafe_allow_html=True)

            # 展示AI追问
            if st.session_state.get(f"show_ai_{cid}", False):
                qs = st.session_state.get(f"ai_q_{cid}", [])
                if qs:
                    items_html = "".join(f'<div class="ai-q-item">{q}</div>' for q in qs)
                    st.markdown(f"""
                    <div class="ai-questions">
                        <div class="block-label" style="margin-top:0;">审稿人可能针对本文追问</div>
                        {items_html}
                    </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 主界面
# ──────────────────────────────────────────────

def main():
    # 标题
    st.markdown("""
    <div class="pst-header">
        <h1>论文压力测试 · Paper Stress Test</h1>
        <p>投稿前系统扫描 · 中文经管顶刊审稿人视角 · 覆盖结构 / DID / IV</p>
    </div>
    """, unsafe_allow_html=True)

    # 上传
    uploaded = st.file_uploader(
        "上传论文 PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded is None:
        st.markdown("""
        <div class="upload-hint">
            将 PDF 拖拽至上方，或点击上传<br>
            <span style="font-size:0.75rem;">支持中英文论文 · 检测结果不会上传或储存</span>
        </div>
        """, unsafe_allow_html=True)
        return

    # 检测
    cache_key = f"result_{uploaded.name}_{uploaded.size}"
    if cache_key not in st.session_state:
        with st.spinner(f"正在分析 {uploaded.name} ..."):
            engine = PaperEngine()
            result = engine.analyze(uploaded.read())
            st.session_state[cache_key] = result
            st.session_state["excerpt"] = result["intro_excerpt"]

    result = st.session_state[cache_key]
    excerpt = st.session_state.get("excerpt", "")

    struct      = result["structure"]
    did_type    = result["did_type"]
    did_results = result["did_results"]
    iv_results  = result["iv_results"]

    # 总分
    render_score_row(struct, did_results, iv_results)

    # 结构层
    render_structure(struct)

    # DID层
    if did_type:
        label = "DID · 主识别策略（完整追问）" if did_type == "main" else "DID · 稳健性检验（精简追问）"
        st.markdown(f'<div class="sec-title">第二层A · DID方法专项追问</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="method-badge">{label}</div>', unsafe_allow_html=True)
        render_method_cards(did_results, "did", excerpt)

    # IV层
    if result["has_iv"]:
        st.markdown('<div class="sec-title">第二层B · 工具变量（IV）专项追问</div>', unsafe_allow_html=True)
        st.markdown('<div class="method-badge">IV · 工具变量 · 2SLS</div>', unsafe_allow_html=True)
        render_method_cards(iv_results, "iv", excerpt)

    if not did_type and not result["has_iv"]:
        st.markdown("""
        <div style="color:#aaa;font-size:0.85rem;padding:1rem 0;font-family:'JetBrains Mono',monospace;">
        未检测到 DID 或 IV 方法 · RDD模块开发中
        </div>
        """, unsafe_allow_html=True)

    # 页脚
    st.markdown("""
    <div style="margin-top:4rem;padding-top:1rem;border-top:1px solid #e5e5e5;
                font-family:'JetBrains Mono',monospace;font-size:0.7rem;color:#ccc;">
        Paper Stress Test · 覆盖方法：DID · IV · RDD（开发中）
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
