"""同态待办 · 拍照断舍离可交互原型。"""

from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass

import streamlit as st


st.set_page_config(
    page_title="同态待办 · 拍照断舍离",
    page_icon="◌",
    layout="centered",
    initial_sidebar_state="collapsed",
)


@dataclass(frozen=True)
class Suggestion:
    action: str
    reason: str
    space: float


ACTIONS = ["留下", "卖掉", "捐出", "丢弃"]
ACTION_META = {
    "留下": ("留", "keep", "继续使用"),
    "卖掉": ("卖", "sell", "拍照挂闲鱼"),
    "捐出": ("捐", "donate", "清洁后装袋捐出"),
    "丢弃": ("扔", "discard", "分类后丢弃"),
}

DEMO_ITEMS = [
    {"name": "闲置咖啡机", "suggestion": "卖掉", "reason": "近一年很少使用，成色尚好，还有转售价值。", "space": 0.04},
    {"name": "三件旧外套", "suggestion": "捐出", "reason": "状态完好但不再合身，捐出比闲置更有价值。", "space": 0.09},
    {"name": "旅行纪念相册", "suggestion": "留下", "reason": "可能承载独特回忆，建议先确认情感价值。", "space": 0.01},
    {"name": "破损收纳盒", "suggestion": "丢弃", "reason": "已经破损且修复成本高，继续保留的价值较低。", "space": 0.03},
]


def init_state() -> None:
    defaults = {
        "page": "home",
        "items": [],
        "photos": [],
        "done": {},
        "demo": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Streamlit Cloud may keep browser session state across a redeploy. Normalize
    # stale values left by an earlier version so deep pages cannot crash.
    if not isinstance(st.session_state.items, list):
        st.session_state.items = []
    if not isinstance(st.session_state.photos, list):
        st.session_state.photos = []
    if not isinstance(st.session_state.done, dict):
        st.session_state.done = {}
    if st.session_state.page not in {"home", "upload", "review", "tasks", "complete"}:
        st.session_state.page = "home"
    if st.session_state.page in {"review", "tasks", "complete"} and not st.session_state.items:
        st.session_state.page = "home"


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


def reset() -> None:
    for key in ("items", "photos", "done"):
        st.session_state[key] = [] if key != "done" else {}
    st.session_state.demo = False
    st.session_state.page = "home"
    st.rerun()


def mock_suggestion(filename: str, index: int) -> Suggestion:
    """Stable prototype suggestion; replace with a vision model in production."""
    digest = int(hashlib.sha256(filename.encode("utf-8")).hexdigest()[:8], 16)
    choices = [
        Suggestion("卖掉", "看起来仍有使用价值，如果长期闲置，可以先尝试转卖。", 0.04),
        Suggestion("捐出", "状态似乎尚可，送给需要的人比继续积灰更合适。", 0.05),
        Suggestion("留下", "可能仍有使用或情感价值，建议先确认最近一次使用时间。", 0.02),
        Suggestion("丢弃", "如果已经损坏或过期，建议分类处理，别再占用空间。", 0.03),
    ]
    return choices[(digest + index) % len(choices)]


def analyze_uploads(files) -> None:
    items = []
    for index, uploaded in enumerate(files):
        suggestion = mock_suggestion(uploaded.name, index)
        clean_name = uploaded.name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        items.append(
            {
                "name": clean_name or f"物品 {index + 1}",
                "suggestion": suggestion.action,
                "reason": suggestion.reason,
                "space": suggestion.space,
            }
        )
    st.session_state.items = items
    st.session_state.photos = files
    st.session_state.done = {i: False for i in range(len(items))}
    st.session_state.demo = False
    go("review")


def load_demo() -> None:
    st.session_state.items = [item.copy() for item in DEMO_ITEMS]
    st.session_state.photos = []
    st.session_state.done = {i: False for i in range(len(DEMO_ITEMS))}
    st.session_state.demo = True
    go("review")


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
:root{--bg:#f5f1e9;--paper:#fffdf9;--ink:#292620;--soft:#736c61;--line:#e5ded2;--green:#4c765f;--red:#b95c45;--gold:#b6842f;--blue:#657596}
.stApp{background:radial-gradient(circle at 50% -15%,#fff 0,#f5f1e9 42%,#ebe5db 100%);color:var(--ink);font-family:'Noto Sans SC',sans-serif}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer{visibility:hidden}
.block-container{max-width:680px;padding:2.2rem 1.25rem 5rem}
h1,h2,h3,p{color:var(--ink)}
.brand{font-size:14px;font-weight:700;letter-spacing:.08em;color:#5d574e;margin-bottom:2.8rem}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.14em;color:#8a8174;margin-bottom:.7rem;text-transform:uppercase}
.hero-title{font-size:clamp(32px,8vw,48px);line-height:1.2;font-weight:700;letter-spacing:-.04em;margin:0 0 1rem}
.hero-copy{font-size:16px;line-height:1.8;color:var(--soft);max-width:520px;margin-bottom:2rem}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:2rem 0}
.step{background:rgba(255,253,249,.72);border:1px solid var(--line);border-radius:16px;padding:16px 12px;min-height:105px}
.step b{display:block;font-size:12px;color:#9b9285;margin-bottom:12px}.step span{font-size:14px;font-weight:600;line-height:1.45}
.notice{background:#eee8dd;border-radius:14px;padding:13px 15px;color:#6e675d;font-size:12px;line-height:1.7;margin:1.2rem 0}
.topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.2rem}.counter{font-size:13px;color:var(--soft)}
.section-title{font-size:28px;font-weight:700;letter-spacing:-.03em;margin:.25rem 0 .55rem}.section-copy{color:var(--soft);font-size:14px;line-height:1.7;margin-bottom:1.4rem}
.card{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:18px;margin:12px 0;box-shadow:0 8px 24px rgba(68,57,42,.04)}
.item-head{display:flex;gap:10px;align-items:center;margin-bottom:10px}.pill{padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700}.pill.keep{background:#e7f0ea;color:var(--green)}.pill.sell{background:#faf0dc;color:var(--gold)}.pill.donate{background:#e9edf5;color:var(--blue)}.pill.discard{background:#f8e9e4;color:var(--red)}
.item-name{font-size:16px;font-weight:700}.reason{font-size:13px;line-height:1.65;color:var(--soft);margin:0}.task{font-size:13px;color:#8c8376;margin-top:9px}
.success-ring{width:92px;height:92px;border-radius:50%;background:#dfece4;color:var(--green);display:flex;align-items:center;justify-content:center;font-size:42px;margin:2.5rem auto 1.4rem}
.summary{text-align:center;background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:24px;margin:1.5rem 0}.big-number{font-size:38px;font-weight:700}.summary-grid{display:grid;grid-template-columns:1fr 1px 1fr;gap:18px;align-items:center}.vline{height:52px;background:var(--line)}
.fineprint{text-align:center;font-size:11px;color:#9a9287;margin-top:2rem;line-height:1.7}
.stButton>button{border-radius:14px;min-height:48px;font-weight:700;border:1px solid var(--ink);transition:.15s;background:#fffdf9;color:var(--ink)}
.stButton>button p,.stButton>button span{color:inherit!important}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:var(--ink)!important;border-color:var(--ink)!important;color:#fff!important}
.stButton>button[kind="primary"] p,.stButton>button[kind="primary"] span,.stButton>button[data-testid="stBaseButton-primary"] p,.stButton>button[data-testid="stBaseButton-primary"] span{color:#fff!important}
.stButton>button:hover{transform:translateY(-1px);border-color:var(--ink)}
.stButton>button:disabled,.stButton>button:disabled p,.stButton>button:disabled span{color:#a39b90!important;background:#e8e2d8!important;border-color:#d7cfc3!important}
[data-testid="stFileUploader"]{background:rgba(255,253,249,.8);border:1.5px dashed #bdb3a5;border-radius:20px;padding:14px}[data-testid="stFileUploaderDropzone"]{background:transparent}
[data-testid="stProgressBar"]>div>div{background:var(--green)}
@media(max-width:520px){.block-container{padding-top:1.3rem}.brand{margin-bottom:2rem}.steps{gap:7px}.step{padding:13px 9px}.step span{font-size:12px}}
</style>
""",
    unsafe_allow_html=True,
)

init_state()

st.markdown('<div class="brand">◌ 同态待办</div>', unsafe_allow_html=True)

page = st.session_state.page

if page == "home":
    st.markdown('<div class="eyebrow">拍照断舍离 · 家庭闲置整理</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">拍下来，<br>一件件放下。</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">不替你做决定，只帮你把纠结变成一份能完成的清单。花几分钟，为家里腾出一点呼吸的空间。</div>',
        unsafe_allow_html=True,
    )
    if st.button("开始整理", type="primary", use_container_width=True):
        go("upload")
    if st.button("先体验一个示例", use_container_width=True):
        load_demo()
    st.markdown(
        '<div class="steps"><div class="step"><b>01</b><span>拍下想整理的物品</span></div><div class="step"><b>02</b><span>参考 AI 的处理建议</span></div><div class="step"><b>03</b><span>逐项完成处理待办</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="notice">照片仅用于本次分析，完成整理后不再保留。AI 建议可能不准确，尤其是有纪念意义的物品，请由你做最后决定。</div>', unsafe_allow_html=True)

elif page == "upload":
    st.markdown('<div class="eyebrow">第 1 步 · 拍照</div><div class="section-title">这次想整理什么？</div><div class="section-copy">一次可选多张照片。每张照片尽量只放一件物品，建议会更准确。</div>', unsafe_allow_html=True)
    files = st.file_uploader(
        "上传物品照片",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="支持 JPG、PNG、WebP",
    )
    if files:
        st.caption(f"已选择 {len(files)} 张照片")
        cols = st.columns(min(len(files), 3))
        for index, uploaded in enumerate(files[:6]):
            cols[index % len(cols)].image(uploaded, use_container_width=True)
    if st.button("让 AI 帮我看看", type="primary", use_container_width=True, disabled=not files):
        analyze_uploads(files)
    if st.button("没有照片，使用示例", use_container_width=True):
        load_demo()
    if st.button("← 返回", use_container_width=True):
        go("home")
    st.markdown('<div class="notice">原型说明：当前体验版用示例规则生成建议，正式版将接入视觉模型，并允许你随时修改决定。</div>', unsafe_allow_html=True)

elif page == "review":
    items = st.session_state.items
    st.markdown('<div class="eyebrow">第 2 步 · 看建议</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">AI 看了 {len(items)} 件物品</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">这只是一个起点。你可以按自己的真实感受，修改每一件的处理方式。</div>',
        unsafe_allow_html=True,
    )
    for index, item in enumerate(items):
        label, css, task = ACTION_META[item["suggestion"]]
        safe_name = html.escape(item["name"])
        safe_reason = html.escape(item["reason"])
        st.markdown(
            f'<div class="card"><div class="item-head"><span class="pill {css}">{label}</span><span class="item-name">{safe_name}</span></div><p class="reason">{safe_reason}</p><div class="task">下一步：{task}</div></div>',
            unsafe_allow_html=True,
        )
        new_action = st.selectbox(
            f"修改“{item['name']}”的决定",
            ACTIONS,
            index=ACTIONS.index(item["suggestion"]),
            key=f"action_{index}",
            label_visibility="collapsed",
        )
        item["suggestion"] = new_action
    if st.button("生成我的处理清单", type="primary", use_container_width=True):
        go("tasks")
    if st.button("← 重新选择照片", use_container_width=True):
        go("upload")
    st.markdown('<div class="notice">请特别留意带有回忆、家庭关系或高价值属性的物品。AI 不知道它对你意味着什么。</div>', unsafe_allow_html=True)

elif page == "tasks":
    items = st.session_state.items
    done_count = sum(bool(v) for v in st.session_state.done.values())
    st.markdown(f'<div class="eyebrow">第 3 步 · 去完成</div><div class="section-title">处理清单</div><div class="section-copy">{done_count}/{len(items)} 已完成。做完一件，就把它轻轻划掉。</div>', unsafe_allow_html=True)
    st.progress(done_count / len(items) if items else 0)
    for index, item in enumerate(items):
        _, css, task = ACTION_META[item["suggestion"]]
        checked = st.checkbox(
            f"{item['name']} · {task}",
            value=st.session_state.done.get(index, False),
            key=f"done_{index}",
        )
        st.session_state.done[index] = checked
    done_count = sum(bool(v) for v in st.session_state.done.values())
    if done_count == len(items) and items:
        if st.button("完成本次断舍离", type="primary", use_container_width=True):
            # Uploaded photo objects are deliberately dropped at completion.
            st.session_state.photos = []
            go("complete")
    else:
        st.info(f"再处理 {len(items) - done_count} 件，就完成这次整理了。")
    if st.button("← 调整处理建议", use_container_width=True):
        go("review")

elif page == "complete":
    items = st.session_state.items
    released = sum(item["space"] for item in items if item["suggestion"] != "留下")
    st.markdown('<div class="success-ring">✓</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="text-align:center">本次断舍离完成</div><div class="section-copy" style="text-align:center">你没有追求一次清空，而是认真处理了每一个决定。</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="summary"><div class="summary-grid"><div><div class="big-number">{len(items)}</div><div class="reason">处理物品</div></div><div class="vline"></div><div><div class="big-number">≈ {released:.2f}m³</div><div class="reason">预计腾出空间</div></div></div></div>',
        unsafe_allow_html=True,
    )
    actions = {action: sum(1 for item in items if item["suggestion"] == action) for action in ACTIONS}
    st.caption(" · ".join(f"{action} {count} 件" for action, count in actions.items() if count))
    st.success(f"本次断舍离完成，处理 {len(items)} 件，预计腾出 {released:.2f}m³ 空间。")
    if st.button("开始新一轮整理", type="primary", use_container_width=True):
        reset()
    st.markdown('<div class="fineprint">本次上传的照片已从会话中移除，仅保留处理结果。<br>空间数据为原型阶段的估算值。</div>', unsafe_allow_html=True)
