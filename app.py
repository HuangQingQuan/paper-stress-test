"""
实证研究 AI Co-Pilot — MVP 版本
优先落地：阶段二（识别策略 + 规格预登记）→ 阶段三（执行流水线）→ 阶段四（异常诊断）

硅基流动 API（OpenAI 兼容）：https://api.siliconflow.cn/v1
"""

import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import json
import datetime
import io
import os
from openai import OpenAI

# ─────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────
st.set_page_config(
    page_title="实证研究 AI Co-Pilot",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# 全局样式
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #0F0F14; }
    .block-container { padding-top: 2rem; }
    .phase-header {
        background: linear-gradient(90deg, #1A1A2E 0%, #0F0F14 100%);
        border-left: 3px solid #00C48C;
        padding: 12px 20px;
        margin: 16px 0 8px 0;
        border-radius: 0 4px 4px 0;
    }
    .decision-header {
        border-left-color: #FF6B35 !important;
    }
    .locked-badge {
        background: #00C48C20;
        color: #00C48C;
        border: 1px solid #00C48C40;
        padding: 3px 10px;
        border-radius: 3px;
        font-size: 11px;
        letter-spacing: 1px;
    }
    .warning-badge {
        background: #FF6B3520;
        color: #FF6B35;
        border: 1px solid #FF6B3540;
        padding: 3px 10px;
        border-radius: 3px;
        font-size: 11px;
    }
    .audit-log {
        background: #0A0A10;
        border: 1px solid #1E1E2E;
        border-radius: 4px;
        padding: 12px;
        font-family: monospace;
        font-size: 12px;
        color: #888;
        max-height: 300px;
        overflow-y: auto;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Session State 初始化
# ─────────────────────────────────────────
defaults = {
    "api_key": "",
    "research_question": "",
    "strategies": [],          # AI 生成的识别策略方案
    "selected_strategy": None, # 人类选定的策略
    "spec_list": {},           # 预登记的规格列表
    "spec_locked": False,      # 闸门：规格是否已锁定
    "data": None,              # 上传的数据集
    "results": [],             # 回归结果列表
    "audit_log": [],           # 审计日志
    "anomalies": [],           # 异常标记
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.audit_log.append(f"[{ts}] [{level}] {msg}")


def get_client():
    return OpenAI(
        api_key=st.session_state.api_key,
        base_url="https://api.siliconflow.cn/v1"
    )


def call_ai(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    client = get_client()
    kwargs = dict(
        model="deepseek-ai/DeepSeek-V3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# ─────────────────────────────────────────
# 侧边栏：API 配置 + 审计日志
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ◈ 实证研究 Co-Pilot")
    st.caption("硅基流动 · DeepSeek-V3")
    st.divider()

    api_key = st.text_input(
        "硅基流动 API Key",
        type="password",
        value=st.session_state.api_key,
        placeholder="sk-...",
    )
    if api_key:
        st.session_state.api_key = api_key
        st.success("API Key 已设置 ✓")

    st.divider()

    # 流程进度
    st.markdown("**流程进度**")
    steps = [
        ("阶段二：识别策略", bool(st.session_state.strategies)),
        ("规格预登记", st.session_state.spec_locked),
        ("阶段三：数据执行", bool(st.session_state.results)),
        ("阶段四：异常诊断", bool(st.session_state.anomalies)),
    ]
    for name, done in steps:
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} {name}")

    st.divider()

    # 重置按钮
    if st.button("🔄 重置全部", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

    st.divider()
    st.markdown("**审计日志**")
    if st.session_state.audit_log:
        log_text = "\n".join(st.session_state.audit_log[-50:])
        st.markdown(f'<div class="audit-log">{log_text}</div>', unsafe_allow_html=True)
        log_bytes = "\n".join(st.session_state.audit_log).encode("utf-8")
        st.download_button(
            "📥 导出完整日志",
            data=log_bytes,
            file_name=f"audit_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            use_container_width=True,
        )
    else:
        st.caption("暂无日志记录")


# ─────────────────────────────────────────
# 主区域：Tab 布局
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📋 阶段二：识别策略 & 预登记",
    "⚙️  阶段三：执行流水线",
    "🔍 阶段四：异常诊断"
])


# ══════════════════════════════════════════
# TAB 1 — 阶段二：识别策略 + 规格预登记
# ══════════════════════════════════════════
with tab1:
    st.markdown('<div class="phase-header decision-header"><b>阶段二：识别策略设计 ＋ 规格列表预登记</b><br><small>人类强力把关 · 核心决策闸门</small></div>', unsafe_allow_html=True)

    col_q, col_btn = st.columns([4, 1])
    with col_q:
        rq = st.text_area(
            "研究问题",
            value=st.session_state.research_question,
            placeholder="例：最低工资上调对低技能劳动力就业率的因果效应",
            height=80,
        )
        if rq:
            st.session_state.research_question = rq
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        gen_btn = st.button(
            "AI 生成方案",
            use_container_width=True,
            disabled=not (st.session_state.api_key and rq),
            type="primary",
        )

    if gen_btn:
        with st.spinner("AI 正在分析识别策略..."):
            try:
                system = """你是一位顶尖的计量经济学专家。请为给定的研究问题生成识别策略方案。
严格返回 JSON，格式：
{
  "strategies": [
    {
      "id": 1,
      "name": "策略名称",
      "method": "计量方法（OLS/IV/DID/RDD/...）",
      "logic": "识别逻辑（2-3句）",
      "assumption": "核心假设",
      "risk": "主要风险",
      "feasibility": "可行性评分（1-5）"
    }
  ]
}
生成3-4个不同维度的策略。只输出 JSON，不要任何其他文字。"""
                content = call_ai(system, f"研究问题：{rq}", json_mode=True)
                data = json.loads(content)
                st.session_state.strategies = data.get("strategies", [])
                log(f"AI 生成识别策略 {len(st.session_state.strategies)} 个，研究问题：{rq}")
            except Exception as e:
                st.error(f"API 调用失败：{e}")
                log(f"API 调用失败：{e}", "ERROR")

    # 展示策略
    if st.session_state.strategies:
        st.markdown("#### AI 提案（请选择一项后拍板）")
        selected_id = st.radio(
            "选择识别策略",
            options=[s["id"] for s in st.session_state.strategies],
            format_func=lambda x: next(
                f"方案{s['id']}｜{s['method']}｜{s['name']}"
                for s in st.session_state.strategies if s["id"] == x
            ),
            label_visibility="collapsed",
        )

        # 详情卡片
        sel = next((s for s in st.session_state.strategies if s["id"] == selected_id), None)
        if sel:
            c1, c2, c3 = st.columns(3)
            c1.metric("计量方法", sel["method"])
            c2.metric("可行性评分", f"{sel['feasibility']} / 5")
            c3.metric("核心假设", "需人工确认")
            with st.expander("查看详情"):
                st.markdown(f"**识别逻辑**：{sel['logic']}")
                st.markdown(f"**核心假设**：{sel['assumption']}")
                st.warning(f"⚠ 主要风险：{sel['risk']}")

        st.divider()

        # ── 规格列表预登记（关键闸门）──
        st.markdown("#### 规格列表预登记 ⚠ 锁定后不可修改")

        if not st.session_state.spec_locked:
            with st.form("spec_form"):
                st.caption("在此锁定回归规格。锁定后 AI 才会释放执行层。")
                col1, col2 = st.columns(2)
                with col1:
                    dep_var = st.text_input("因变量（Y）", placeholder="employment_rate")
                    indep_vars = st.text_area("自变量（逗号分隔）", placeholder="min_wage, gdp_growth, unemployment_lag")
                    control_vars = st.text_area("控制变量（逗号分隔）", placeholder="age, education, industry")
                with col2:
                    cluster_level = st.selectbox("聚类层级", ["无", "个体", "省份/地区", "行业", "时间"])
                    sample_filter = st.text_area("样本筛选规则", placeholder="年份 >= 2010，排除农业部门")
                    fe_type = st.selectbox("固定效应", ["无", "个体固定效应", "时间固定效应", "双向固定效应"])
                    robustness_checks = st.multiselect(
                        "预设稳健性检验",
                        ["更换子样本", "增减控制变量", "替换核心自变量", "更换聚类层级", "安慰剂检验"],
                        default=["更换子样本", "增减控制变量"],
                    )

                confirmed = st.checkbox("我已确认工具变量合理性 / 识别假设成立，同意锁定以上规格")
                lock_btn = st.form_submit_button("🔒 锁定规格列表（不可逆）", type="primary")

                if lock_btn:
                    if not confirmed:
                        st.error("请先勾选确认框")
                    elif not dep_var or not indep_vars:
                        st.error("请至少填写因变量和自变量")
                    else:
                        st.session_state.spec_list = {
                            "strategy": sel,
                            "dep_var": dep_var.strip(),
                            "indep_vars": [v.strip() for v in indep_vars.split(",") if v.strip()],
                            "control_vars": [v.strip() for v in control_vars.split(",") if v.strip()],
                            "cluster_level": cluster_level,
                            "sample_filter": sample_filter,
                            "fe_type": fe_type,
                            "robustness_checks": robustness_checks,
                            "locked_at": datetime.datetime.now().isoformat(),
                        }
                        st.session_state.spec_locked = True
                        log(f"规格列表已锁定 | 方法：{sel['method']} | Y={dep_var} | X={indep_vars}", "LOCK")
                        st.success("✅ 规格已锁定，可进入阶段三执行")
                        st.rerun()
        else:
            # 展示已锁定规格
            spec = st.session_state.spec_list
            st.markdown('<span class="locked-badge">🔒 已锁定</span>', unsafe_allow_html=True)
            st.markdown(f"**锁定时间**：{spec.get('locked_at', 'N/A')}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**计量方法**：{spec['strategy']['method']}")
                st.markdown(f"**因变量**：`{spec['dep_var']}`")
                st.markdown(f"**自变量**：`{', '.join(spec['indep_vars'])}`")
                st.markdown(f"**控制变量**：`{', '.join(spec['control_vars']) or '无'}`")
            with col2:
                st.markdown(f"**固定效应**：{spec['fe_type']}")
                st.markdown(f"**聚类层级**：{spec['cluster_level']}")
                st.markdown(f"**稳健性检验**：{', '.join(spec['robustness_checks'])}")


# ══════════════════════════════════════════
# TAB 2 — 阶段三：执行流水线
# ══════════════════════════════════════════
with tab2:
    st.markdown('<div class="phase-header"><b>阶段三：生产流水线</b><br><small>AI 全自动 · 审计日志全程记录</small></div>', unsafe_allow_html=True)

    # 闸门检查
    if not st.session_state.spec_locked:
        st.warning("⚠ 执行层已锁定：请先完成阶段二的规格预登记。")
        st.stop()

    # 数据上传
    st.markdown("#### 数据上传")
    uploaded = st.file_uploader("上传 CSV 数据集", type=["csv"])
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.session_state.data = df
            log(f"数据集已加载：{df.shape[0]} 行 × {df.shape[1]} 列，文件：{uploaded.name}")
            st.success(f"✓ 数据已载入：{df.shape[0]} 行 × {df.shape[1]} 列")
        except Exception as e:
            st.error(f"数据读取失败：{e}")
            log(f"数据读取失败：{e}", "ERROR")

    # 演示数据（若无上传）
    if st.session_state.data is None:
        if st.button("使用演示数据集（最低工资·就业率）"):
            np.random.seed(42)
            n = 300
            demo_df = pd.DataFrame({
                "employment_rate": 0.75 - 0.12 * np.random.rand(n) + np.random.randn(n) * 0.05,
                "min_wage": 8 + 4 * np.random.rand(n),
                "gdp_growth": np.random.randn(n) * 2 + 3,
                "unemployment_lag": 0.05 + 0.03 * np.random.rand(n),
                "age": np.random.randint(20, 60, n),
                "education": np.random.randint(1, 5, n),
                "industry": np.random.choice(["manufacturing", "service", "construction"], n),
                "year": np.random.choice(range(2010, 2024), n),
                "region": np.random.choice(["east", "west", "central"], n),
            })
            st.session_state.data = demo_df
            log("演示数据集已加载：300 行 × 9 列")
            st.success("✓ 演示数据已载入")
            st.rerun()

    df = st.session_state.data
    if df is not None:
        spec = st.session_state.spec_list
        dep = spec["dep_var"]
        indeps = spec["indep_vars"]
        controls = spec["control_vars"]

        st.markdown("#### 数据质量诊断")
        with st.expander("展开诊断报告", expanded=True):
            cols_needed = [dep] + indeps + controls
            available = [c for c in cols_needed if c in df.columns]
            missing_cols = [c for c in cols_needed if c not in df.columns]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总行数", df.shape[0])
            c2.metric("总列数", df.shape[1])
            c3.metric("缺失值比例", f"{df.isnull().mean().mean():.1%}")
            c4.metric("关键变量可用", f"{len(available)}/{len(cols_needed)}")

            if missing_cols:
                st.warning(f"⚠ 以下变量在数据集中不存在：{missing_cols}。将使用可用变量执行。")
                log(f"变量缺失：{missing_cols}", "WARN")

            if available:
                st.dataframe(
                    df[available].describe().round(3),
                    use_container_width=True,
                )
                log(f"数据质量诊断完成：{len(available)} 个变量可用")

        st.divider()
        st.markdown("#### 执行回归")

        run_btn = st.button("▶ 执行预登记规格（Baseline 回归）", type="primary")

        if run_btn:
            results_store = []
            log("开始执行 Baseline 回归...")

            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            regressors = [v for v in (indeps + controls) if v in numeric_cols and v != dep]
            y_col = dep if dep in numeric_cols else None

            skipped = [v for v in (indeps + controls + [dep]) if v in df.columns and v not in numeric_cols]
            if skipped:
                st.warning(f"⚠ 以下变量为非数值类型，已自动跳过（如需使用请先做哑变量编码）：{skipped}")
                log(f"非数值变量跳过：{skipped}", "WARN")

            if not y_col or not regressors:
                st.error("因变量或自变量在数据集中不存在或均为非数值类型，无法执行回归。")
                log("回归失败：无有效数值变量", "ERROR")
            else:
                df_clean = df[[y_col] + regressors].dropna()
                log(f"清洗后样本量：{len(df_clean)} 行（原始 {len(df)} 行）")

                # Baseline OLS
                try:
                    X = sm.add_constant(df_clean[regressors])
                    y = df_clean[y_col]
                    model = sm.OLS(y, X).fit(cov_type='HC3')
                    results_store.append({
                        "label": "Baseline OLS",
                        "model": model,
                        "n": len(df_clean),
                    })
                    log(f"Baseline OLS 完成：R²={model.rsquared:.4f}，N={len(df_clean)}")
                except Exception as e:
                    st.error(f"Baseline 回归失败：{e}")
                    log(f"Baseline 回归失败：{e}", "ERROR")

                # 稳健性：减少控制变量
                if "增减控制变量" in spec.get("robustness_checks", []) and controls:
                    try:
                        regressors_r = [v for v in indeps if v in numeric_cols]
                        if regressors_r:
                            X_r = sm.add_constant(df_clean[regressors_r])
                            model_r = sm.OLS(y, X_r).fit(cov_type='HC3')
                            results_store.append({
                                "label": "稳健性：仅核心自变量",
                                "model": model_r,
                                "n": len(df_clean),
                            })
                            log(f"稳健性（无控制变量）完成：R²={model_r.rsquared:.4f}")
                    except Exception as e:
                        log(f"稳健性回归失败：{e}", "WARN")

                # 稳健性：子样本
                if "更换子样本" in spec.get("robustness_checks", []) and "year" in df.columns:
                    try:
                        df_sub = df_clean[df["year"].isin(df["year"].unique()[::2])[:len(df_clean)]]
                        if len(df_sub) > 30:
                            X_s = sm.add_constant(df_sub[regressors])
                            model_s = sm.OLS(df_sub[y_col], X_s).fit(cov_type='HC3')
                            results_store.append({
                                "label": "稳健性：奇数年子样本",
                                "model": model_s,
                                "n": len(df_sub),
                            })
                            log(f"稳健性（子样本）完成：N={len(df_sub)}，R²={model_s.rsquared:.4f}")
                    except Exception as e:
                        log(f"子样本稳健性失败：{e}", "WARN")

                st.session_state.results = results_store

        # 展示结果
        if st.session_state.results:
            st.markdown("#### 回归结果")
            for res in st.session_state.results:
                with st.expander(f"📊 {res['label']}（N={res['n']}）", expanded=True):
                    m = res["model"]
                    summary_df = pd.DataFrame({
                        "系数": m.params.round(4),
                        "标准误": m.bse.round(4),
                        "t 值": m.tvalues.round(3),
                        "p 值": m.pvalues.round(4),
                        "95% CI 下界": m.conf_int()[0].round(4),
                        "95% CI 上界": m.conf_int()[1].round(4),
                    })
                    # 标红 p < 0.1
                    def highlight_sig(row):
                        p = row["p 值"]
                        if p < 0.01:
                            return ["background-color: #00C48C20"] * len(row)
                        elif p < 0.05:
                            return ["background-color: #00C48C10"] * len(row)
                        elif p < 0.1:
                            return ["background-color: #FF6B3510"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        summary_df.style.apply(highlight_sig, axis=1),
                        use_container_width=True,
                    )
                    col1, col2, col3 = st.columns(3)
                    col1.metric("R²", f"{m.rsquared:.4f}")
                    col2.metric("Adj. R²", f"{m.rsquared_adj:.4f}")
                    col3.metric("F 统计量 p 值", f"{m.f_pvalue:.4f}")


# ══════════════════════════════════════════
# TAB 3 — 阶段四：异常诊断
# ══════════════════════════════════════════
with tab3:
    st.markdown('<div class="phase-header"><b>阶段四：异常诊断 ＋ 人类解释</b><br><small>AI 标记症状 · 人类开处方</small></div>', unsafe_allow_html=True)

    if not st.session_state.results:
        st.info("请先完成阶段三的回归执行。")
        st.stop()

    # 自动异常检测
    if st.button("🔍 运行自动异常检测", type="primary"):
        anomalies = []
        spec = st.session_state.spec_list

        for res in st.session_state.results:
            m = res["model"]
            label = res["label"]

            # 检测1：系数符号检查（核心自变量）
            for var in spec.get("indep_vars", []):
                if var in m.params.index:
                    coef = m.params[var]
                    pval = m.pvalues[var]
                    if abs(coef) > 3 * m.bse[var]:
                        anomalies.append({
                            "规格": label, "变量": var,
                            "类型": "系数异常偏大",
                            "详情": f"系数 {coef:.4f} 超过标准误 3 倍以上，疑似异常值影响",
                            "风险等级": "高",
                        })
                        log(f"异常检测：{label} | {var} 系数异常偏大 ({coef:.4f})", "WARN")

            # 检测2：p 值在临界点附近（p-hacking 风险提示）
            for var in m.pvalues.index:
                p = m.pvalues[var]
                if 0.04 < p < 0.06:
                    anomalies.append({
                        "规格": label, "变量": var,
                        "类型": "p 值临界警告",
                        "详情": f"p={p:.4f}，处于 0.05 临界区间，结论稳健性存疑",
                        "风险等级": "中",
                    })
                    log(f"异常检测：{label} | {var} p 值临界 ({p:.4f})", "WARN")

            # 检测3：跨规格系数波动
            if len(st.session_state.results) > 1:
                for var in spec.get("indep_vars", []):
                    coefs = []
                    for r in st.session_state.results:
                        if var in r["model"].params.index:
                            coefs.append(r["model"].params[var])
                    if len(coefs) > 1:
                        cv = np.std(coefs) / abs(np.mean(coefs)) if np.mean(coefs) != 0 else 0
                        if cv > 0.5:
                            anomalies.append({
                                "规格": "跨规格比较", "变量": var,
                                "类型": "跨规格系数波动大",
                                "详情": f"变异系数 {cv:.2f}，不同规格下系数从 {min(coefs):.4f} 到 {max(coefs):.4f}",
                                "风险等级": "高",
                            })
                            log(f"异常检测：{var} 跨规格系数变异系数 {cv:.2f}", "WARN")

            # 检测4：R² 过高或过低
            r2 = m.rsquared
            if r2 > 0.95:
                anomalies.append({
                    "规格": label, "变量": "整体模型",
                    "类型": "R² 异常偏高",
                    "详情": f"R²={r2:.4f}，疑似过拟合或多重共线性",
                    "风险等级": "高",
                })
            elif r2 < 0.01:
                anomalies.append({
                    "规格": label, "变量": "整体模型",
                    "类型": "R² 异常偏低",
                    "详情": f"R²={r2:.4f}，模型解释力极低，检查变量选择",
                    "风险等级": "中",
                })

        st.session_state.anomalies = anomalies
        log(f"异常检测完成：共发现 {len(anomalies)} 个异常")

    # 展示异常
    if st.session_state.anomalies:
        st.markdown(f"#### 检测结果：发现 {len(st.session_state.anomalies)} 个异常")
        anom_df = pd.DataFrame(st.session_state.anomalies)

        risk_color = {"高": "🔴", "中": "🟡", "低": "🟢"}
        for _, row in anom_df.iterrows():
            icon = risk_color.get(row["风险等级"], "⚪")
            with st.expander(f"{icon} [{row['风险等级']}] {row['类型']} · {row['规格']} · {row['变量']}"):
                st.markdown(f"**详情**：{row['详情']}")
                judge = st.radio(
                    "人类判断",
                    ["待确认", "数据质量问题（需回滚重新登记）", "真实经济学机制（可接受）", "需进一步调查"],
                    key=f"judge_{row['类型']}_{row['变量']}_{row['规格']}",
                )
                if judge != "待确认":
                    log(f"人类判断：{row['类型']} | {row['变量']} → {judge}")
                if "回滚" in judge:
                    st.error("⚠ 建议回滚：请返回阶段二重新设计规格并预登记。")

    elif st.session_state.results:
        st.info("点击上方按钮运行异常检测。")

    # AI 辅助解释
    if st.session_state.results and st.session_state.api_key:
        st.divider()
        st.markdown("#### AI 辅助结果解释（草稿，需人类审阅因果语言）")

        if st.button("生成结果解释草稿"):
            spec = st.session_state.spec_list
            m = st.session_state.results[0]["model"]
            results_summary = "\n".join([
                f"变量 {v}: 系数={m.params[v]:.4f}, p={m.pvalues[v]:.4f}"
                for v in m.params.index if v != "const"
            ])
            with st.spinner("生成中..."):
                try:
                    draft = call_ai(
                        """你是经济学论文写作助手。生成回归结果的描述性文字草稿。
重要限制：
1. 仅使用"相关"、"关联"等中性词汇，不使用"导致"、"影响"、"使得"等因果语言
2. 明确标出需要人类确认因果解释的位置，用【需人类确认因果语言】标注
3. 附上提醒：AI 草稿不代表因果推断结论""",
                        f"研究问题：{spec.get('dep_var','Y')} vs {spec.get('indep_vars','X')}\n回归结果：\n{results_summary}",
                    )
                    st.markdown(draft)
                    st.warning("⚠ 以上为 AI 草稿，请仔细审阅因果语言，确保描述与识别策略一致。")
                    log("AI 结果解释草稿已生成，待人类审阅")
                except Exception as e:
                    st.error(f"生成失败：{e}")
