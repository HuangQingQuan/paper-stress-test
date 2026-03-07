"""
engine.py — 规则检测引擎
所有规则、卡片配置和检测逻辑，与UI完全解耦。
"""

import re
import fitz  # PyMuPDF


# ──────────────────────────────────────────────
# 第一层：结构规则（12条）
# ──────────────────────────────────────────────

RULES = [
    {"category": "引言", "scope": "intro", "id": "q1", "name": "研究问题陈述",
     "patterns": [r"(本文|本研究|考察|分析).{0,20}(问题|关系|影响|机制)",
                  r"(this paper|this study).{0,30}(examine|investigate|analyze)"]},

    {"category": "引言", "scope": "intro", "id": "q2", "name": "边际贡献表达",
     "patterns": [r"(区别于|有别于|不同于|弥补.{0,5}缺口|拓展.{0,5}文献|边际贡献)",
                  r"(different from prior|contribut\w+ to the literature|distinguish.{0,20}from)"]},

    {"category": "引言", "scope": "intro", "id": "q3", "name": "预告识别策略",
     "patterns": [r"(双重差分|did(?!actic)|工具变量|断点回归|rdd|合成控制|识别策略|因果识别)",
                  r"(difference.in.difference|instrumental variable|regression discontinuity|natural experiment)"]},

    {"category": "设计", "scope": "all", "id": "q4", "name": "变量测度依据",
     "patterns": [r"(参考|借鉴|遵循|参照).{0,10}(文献|研究|做法|方法)",
                  r"(following|as in|consistent with).{0,20}(we measure|we construct|we define)"]},

    {"category": "设计", "scope": "all", "id": "q5", "name": "基准回归方程",
     "patterns": [r"[yY]\s*[=＝]\s*.{0,10}[αβδεγλ]", r"(α|β|γ|δ|ε)\s*\d",
                  r"(计量模型|基准回归模型).{0,20}(如下|设定|为)",
                  r"(regression model|baseline model).{0,20}(as follows|specified)"]},

    {"category": "设计", "scope": "all", "id": "q6", "name": "内生性来源讨论",
     "patterns": [r"(内生性|反向因果|遗漏变量|选择偏误)",
                  r"(endogeneity|reverse causality|omitted variable|selection bias)"]},

    {"category": "设计", "scope": "all", "id": "q7", "name": "识别策略对应内生性",
     "patterns": [r"(解决|缓解|应对|处理).{0,15}(内生性|偏误|反向因果)",
                  r"(address|mitigate|correct for).{0,20}(endogeneity|bias)"]},

    {"category": "结果", "scope": "all", "id": "q8", "name": "经济显著性解释",
     "patterns": [r"(经济[上的]*显著|经济意义|实际意义|增加.{0,5}%|提升.{0,5}个百分点|变为原来的)",
                  r"(economically significant|economic magnitude|an increase of.{0,15}%|one standard deviation)"]},

    {"category": "结果", "scope": "all", "id": "q9", "name": "机制分析",
     "patterns": [r"(机制分析|影响渠道|传导路径|中介效应)",
                  r"(mechanism|channel|mediating|mediation analysis)"]},

    {"category": "稳健", "scope": "all", "id": "q10", "name": "替换变量检验",
     "patterns": [r"(替换|改用|重新定义|重新测度|替代指标).{0,10}(变量|指标|测度|定义)",
                  r"(alternative (measure|proxy|definition|indicator)|replace.{0,15}variable)"]},

    {"category": "稳健", "scope": "all", "id": "q11", "name": "替换样本/时间窗口",
     "patterns": [r"(剔除|子样本|时间窗口|滞后.{0,3}期)",
                  r"(subsample|exclude|time window|lagged)"]},

    {"category": "稳健", "scope": "all", "id": "q12", "name": "排除竞争性解释",
     "patterns": [r"(安慰剂|伪政策|排除.{0,10}(替代|竞争性))",
                  r"(placebo|alternative explanation|rule out|falsification)"]},
]


# ──────────────────────────────────────────────
# 第二层：DID追问卡片
# ──────────────────────────────────────────────

DID_CARDS = [
    {
        "id": "did_1", "title": "平行趋势检验", "risk": "high", "main_only": True,
        "detect_patterns": [r"平行趋势", r"parallel trend", r"pre.?trend",
                            r"事件研究", r"event.?stud", r"lead.{0,5}lag",
                            r"前期系数", r"政策前.{0,5}(期|年)"],
        "question": "未检测到平行趋势检验（图表或lead-lag回归）。",
        "why": "平行趋势是DID识别的核心假设：处理组和对照组在政策冲击前应有相同趋势。这是审稿人第一个会检验的点，缺失通常直接导致大修甚至拒稿。",
        "how": [
            "补法一（推荐）：画事件研究图（event study plot），展示政策前各期系数不显著、政策后系数显著。",
            "补法二：做lead-lag回归，加入政策前2-3期和政策后各期的交互项，在图上展示置信区间。",
            "补法三：如果政策冲击过于集中无法画图，需在文中明确说明原因，并提供替代证据。",
        ],
    },
    {
        "id": "did_2", "title": "Anticipation Effect（预期效应）", "risk": "medium", "main_only": True,
        "detect_patterns": [r"anticipat", r"预期效应", r"事前效应",
                            r"提前.{0,5}(行动|响应|调整)", r"政策.{0,10}预期",
                            r"突发性", r"不可预期"],
        "question": "未检测到对预期效应（anticipation effect）的讨论。",
        "why": "若企业在政策正式实施前已预期到冲击并提前调整行为，会导致政策前期系数也显著，污染平行趋势图，审稿人通常会追问。",
        "how": [
            "补法一：在事件研究图中，若政策前1期系数不显著，可作为无预期效应的证据。",
            "补法二：文中讨论该政策是否具有突发性/不可预期性，提供政策出台背景支撑。",
            "补法三：剔除政策实施前1年样本重新回归，验证结论稳健。",
        ],
    },
    {
        "id": "did_3", "title": "安慰剂检验（Placebo Test）", "risk": "high", "main_only": False,
        "detect_patterns": [r"安慰剂", r"placebo", r"伪政策", r"randomly assign",
                            r"随机(分配|置换|抽取)", r"虚构.{0,5}(政策|时间|处理)", r"falsif"],
        "question": "未检测到安慰剂检验（placebo test）。",
        "why": "安慰剂检验用于排除结果由随机因素驱动的可能性。常见方式是随机置换处理组或虚构政策时间，若系数依然显著说明结果不可信。中文顶刊近年对此要求越来越严格。",
        "how": [
            "补法一（时间安慰剂）：将政策时间前移2-3年重新回归，系数应不显著。",
            "补法二（样本安慰剂）：在从未受到政策影响的样本中随机指定处理组回归，系数应不显著。",
            "补法三（随机置换）：对处理变量做500次随机置换，绘制系数分布图，真实系数应在分布尾部。",
        ],
    },
    {
        "id": "did_4", "title": "动态效应分析", "risk": "medium", "main_only": True,
        "detect_patterns": [r"动态效应", r"dynamic effect", r"政策效果.{0,10}持续",
                            r"长期.{0,10}短期", r"逐年.{0,5}(系数|效果|影响)",
                            r"各期.{0,5}系数", r"时间异质"],
        "question": "未检测到政策动态效应分析（短期vs长期效果）。",
        "why": "仅报告平均处理效应（ATT）不够，审稿人会问：政策效果是立竿见影还是逐渐累积？是否随时间衰减？动态效应分析也能同时作为平行趋势证据。",
        "how": [
            "在事件研究图中同时展示政策前各期（pre-trend）和政策后各期（dynamic effect），一张图同时回答两个问题，效率最高。",
        ],
    },
    {
        "id": "did_5", "title": "处理组与对照组可比性", "risk": "medium", "main_only": True,
        "detect_patterns": [r"倾向得分", r"\bpsm\b", r"propensity score",
                            r"平衡性检验", r"covariate balance", r"共同支撑",
                            r"common support", r"对照组.{0,15}(选择|构建|合理)"],
        "question": "未检测到处理组与对照组可比性的讨论或检验。",
        "why": "若处理组和对照组在政策前系统性不同（规模、行业、地区），DID估计量会有偏。审稿人会质疑：你的对照组是合适的反事实吗？",
        "how": [
            "补法一：报告处理组与对照组在政策前主要特征的均值差异检验（balance table）。",
            "补法二：使用PSM-DID，先匹配再做差分，缩小系统性差异。",
            "补法三：使用合成控制法（Synthetic Control）作为稳健性检验。",
        ],
    },
]


# ──────────────────────────────────────────────
# 第二层：IV追问卡片
# ──────────────────────────────────────────────

IV_CARDS = [
    {
        "id": "iv_1", "title": "第一阶段显著性（相关性）", "risk": "high",
        "detect_patterns": [r"第一阶段", r"first.?stage", r"f.{0,5}统计量",
                            r"\bf.?stat", r"f\s*[>=]\s*1[0-9]",
                            r"(相关性|relevance).{0,20}(工具变量|iv)"],
        "question": "未检测到第一阶段回归结果或F统计量报告。",
        "why": "工具变量的相关性条件要求IV与内生变量显著相关。F统计量<10被视为弱工具变量，会导致2SLS估计量有偏且不一致。这是审稿人收到IV论文后必查的第一个数字。",
        "how": [
            "补法一：明确报告第一阶段回归表格，展示IV对内生变量的系数和显著性。",
            "补法二：报告F统计量，通常要求>10（Staiger & Stock 1997标准）。",
            "补法三：若有多个IV，报告Cragg-Donald F统计量或Kleibergen-Paap rk Wald F统计量。",
        ],
    },
    {
        "id": "iv_2", "title": "排他性限制（Exclusion Restriction）", "risk": "high",
        "detect_patterns": [r"排他性", r"exclusion restriction",
                            r"外生性.{0,20}(工具变量|iv)",
                            r"不直接影响", r"并不直接影响", r"无法直接影响",
                            r"不能直接影响", r"间接.{0,10}(影响|作用).{0,10}(被解释|因变量)",
                            r"排除.{0,10}(限制|条件)", r"满足工具变量.{0,10}(要求|条件)"],
        "question": "未检测到对工具变量排他性（exclusion restriction）的论证。",
        "why": "排他性要求IV只通过内生变量X影响被解释变量Y，不存在其他直接路径。这是IV最难证明的条件，也是审稿人最常打的点，只能靠理论论证，论证越充分越好。",
        "how": [
            "补法一：专门用一段逐条排除IV影响Y的其他路径，逻辑要具体到你的IV。",
            "补法二：引用同类研究中使用相同IV的文献，借助已有共识增强说服力。",
            "补法三：做间接检验——在已知外生的子样本中，若IV对Y影响消失，支持排他性。",
            "注意：审稿人会针对你的具体IV提出挑战，需要逐一预判并在文中回应。",
        ],
    },
    {
        "id": "iv_3", "title": "弱工具变量检验", "risk": "high",
        "detect_patterns": [r"弱工具变量", r"weak instrument", r"cragg.?donald",
                            r"kleibergen.?paap", r"stock.?yogo", r"anderson.?rubin",
                            r"不可识别检验", r"lm\s*(统计量|检验)"],
        "question": "未检测到弱工具变量检验（Cragg-Donald F或Kleibergen-Paap统计量）。",
        "why": "仅报告第一阶段OLS的F统计量不够，在异方差或聚类标准误下失效。规范做法是同时报告不可识别检验（LM统计量）和弱工具变量检验（KP F统计量）。",
        "how": [
            "补法一：使用Stata的ivreg2命令，报告Kleibergen-Paap rk LM统计量和Wald F统计量，对比Stock-Yogo临界值。",
            "补法二：若只有一个IV，第一阶段F>10即可，但仍建议同时报告KP统计量以符合规范。",
            "补法三：Anderson-Rubin检验对弱IV稳健，可作为补充证据。",
        ],
    },
    {
        "id": "iv_4", "title": "过度识别检验（多IV时）", "risk": "medium",
        "detect_patterns": [r"过度识别", r"overidentif", r"sargan",
                            r"hansen.{0,10}(j|检验)", r"j统计量"],
        "question": "使用多个工具变量时，未检测到过度识别检验（Sargan/Hansen J检验）。",
        "why": "当IV个数多于内生变量时，可以检验所有IV的联合外生性。Hansen J统计量不显著说明无法拒绝所有IV均外生的原假设，支持IV有效性。",
        "how": [
            "补法一：使用Stata的ivreg2命令，自动报告Hansen J统计量（需多个IV）。",
            "补法二：若J检验显著（p<0.05），说明至少一个IV可能无效，需重新审视IV选择。",
            "补法三：分别只用其中一个IV跑回归，若结论一致，增强稳健性。",
        ],
    },
    {
        "id": "iv_5", "title": "IV来源与外生性论证", "risk": "high",
        "detect_patterns": [r"工具变量.{0,20}(来源|选取|选择|构建|构造)",
                            r"(选取|选择|使用|采用).{0,10}(作为|作).{0,5}工具变量",
                            r"(历史|地理|气候|制度).{0,20}(作为|作).{0,5}(工具变量|iv)",
                            r"instrument.{0,20}(based on|from|using)",
                            r"工具变量.{0,10}(有效性|合理性|外生)",
                            r"满足工具变量.{0,10}(要求|条件)"],
        "question": "未检测到对工具变量来源和外生性的充分论证。",
        "why": "审稿人会问：为什么这个变量可以作为IV？它凭什么外生于模型？IV的选取逻辑是整篇论文因果推断的根基，论证不充分是最常见的拒稿原因之一。",
        "how": [
            "补法一：专门用一段解释IV的经济学逻辑——为什么它影响X，为什么它不直接影响Y。",
            "补法二：说明IV的来源（历史数据、地理特征、政策变动等），强调其外生性来源。",
            "补法三：引用使用类似IV的已发表文献，借助学界共识背书。",
            "补法四：做敏感性分析，如Conley et al.(2012)的plausibly exogenous方法，放松排他性假设检验结论稳健范围。",
        ],
    },
]


# ──────────────────────────────────────────────
# 核心检测类
# ──────────────────────────────────────────────

class PaperEngine:

    def extract_text(self, pdf_bytes: bytes) -> list[str]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return [page.get_text() for page in doc]

    def clean(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).lower()

    def get_intro_excerpt(self, pages: list[str], max_chars: int = 4000) -> str:
        """返回前3页原始文本，供AI追问使用"""
        return " ".join(pages[:3])[:max_chars]

    def classify_did(self, full_text: str) -> str | None:
        did_patterns = [r"双重差分", r"\bdid\b", r"difference.in.difference",
                        r"双差法", r"准自然实验"]
        if not any(re.search(p, full_text, re.IGNORECASE) for p in did_patterns):
            return None
        robustness_ctx = [
            r"稳健性.{0,30}(双重差分|did)", r"(双重差分|did).{0,30}稳健性",
            r"作为稳健性.{0,20}(检验|分析)", r"稳健性检验.{0,50}(双重差分|did)",
        ]
        main_ctx = [
            r"(研究设计|识别策略|基准回归).{0,80}(双重差分|did)",
            r"(双重差分|did).{0,80}(基准回归|识别策略|研究设计)",
            r"构建.{0,20}(双重差分|did).{0,20}模型",
            r"采用.{0,10}(双重差分|did).{0,10}(方法|模型|检验)",
        ]
        rob = sum(1 for p in robustness_ctx if re.search(p, full_text, re.IGNORECASE))
        main = sum(1 for p in main_ctx if re.search(p, full_text, re.IGNORECASE))
        return 'robustness' if rob > main else 'main'

    def detect_iv(self, ft: str) -> bool:
        return any(re.search(p, ft, re.IGNORECASE) for p in
                   [r"工具变量", r"\biv\b", r"\b2sls\b", r"两阶段最小二乘",
                    r"instrumental variable", r"ivreg"])

    def detect_multiple_iv(self, ft: str) -> bool:
        return any(re.search(p, ft, re.IGNORECASE) for p in
                   [r"两个工具变量", r"多个工具变量", r"过度识别",
                    r"overidentif", r"sargan", r"hansen"])

    def run_structure_check(self, pages: list[str]) -> list[dict]:
        full_text = self.clean(" ".join(pages))
        intro_text = self.clean(" ".join(pages[:3]))
        results = []
        for rule in RULES:
            target = intro_text if rule["scope"] == "intro" else full_text
            found, evidence = False, ""
            for pat in rule["patterns"]:
                m = re.search(pat, target, re.IGNORECASE)
                if m:
                    found = True
                    s, e = max(0, m.start() - 40), min(len(target), m.end() + 80)
                    evidence = f"...{target[s:e]}..."
                    break
            if rule["id"] == "q5" and not found:
                evidence = "未检测到方程（PDF解析可能导致公式乱码，建议人工核查）"
            results.append({
                "id": rule["id"], "category": rule["category"], "name": rule["name"],
                "passed": found,
                "evidence": evidence if found else (
                    evidence if rule["id"] == "q5" else "文中未检测到相关表述，建议补充"
                ),
            })
        return results

    def _run_cards(self, cards, full_text, skip_ids=None):
        skip_ids = skip_ids or []
        results = []
        for card in cards:
            if card["id"] in skip_ids:
                continue
            found = any(re.search(p, full_text, re.IGNORECASE)
                        for p in card["detect_patterns"])
            results.append({
                "id": card["id"], "title": card["title"], "risk": card["risk"],
                "passed": found,
                "question": card["question"],
                "why": card["why"],
                "how": card["how"],
            })
        return results

    def run_did_cards(self, full_text: str, did_type: str) -> list[dict]:
        skip = [c["id"] for c in DID_CARDS
                if did_type == 'robustness' and c.get('main_only', True)]
        return self._run_cards(DID_CARDS, full_text, skip_ids=skip)

    def run_iv_cards(self, full_text: str) -> list[dict]:
        skip = ["iv_4"] if not self.detect_multiple_iv(full_text) else []
        return self._run_cards(IV_CARDS, full_text, skip_ids=skip)

    def analyze(self, pdf_bytes: bytes) -> dict:
        """主入口：返回完整分析结果字典"""
        pages = self.extract_text(pdf_bytes)
        full_text = self.clean(" ".join(pages))
        intro_excerpt = self.get_intro_excerpt(pages)

        struct = self.run_structure_check(pages)
        did_type = self.classify_did(full_text)
        has_iv = self.detect_iv(full_text)

        did_results = self.run_did_cards(full_text, did_type) if did_type else []
        iv_results = self.run_iv_cards(full_text) if has_iv else []

        return {
            "pages": pages,
            "full_text": full_text,
            "intro_excerpt": intro_excerpt,
            "structure": struct,
            "did_type": did_type,
            "has_iv": has_iv,
            "did_results": did_results,
            "iv_results": iv_results,
        }
