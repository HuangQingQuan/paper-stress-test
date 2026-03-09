"""
paper_reader.py — PDF 解析与结构化提取
将论文切分为：摘要、引言、研究设计、实证结果、稳健性、结论
供 reviewer.py 按需取用，避免超出上下文窗口。
"""

import re
import fitz  # PyMuPDF


# 各部分的识别关键词（顺序敏感）
SECTION_PATTERNS = [
    ("abstract",  [r"摘\s*要", r"abstract"]),
    ("intro",     [r"一[、．.]\s*(引言|绪论|研究背景)", r"1[、．.]\s*(引言|绪论|研究背景)",
                   r"^引言$", r"introduction"]),
    ("literature",[r"(二|三)[、．.]\s*(文献|理论|相关研究)", r"(2|3)[、．.]\s*(literature|理论基础)",
                   r"文献综述", r"理论基础与研究假设", r"理论框架"]),
    ("design",    [r"(三|四)[、．.]\s*(研究设计|数据|模型|实证设计)",
                   r"(3|4)[、．.]\s*(研究设计|数据|模型)",
                   r"研究设计", r"data and method", r"empirical strategy"]),
    ("results",   [r"(四|五)[、．.]\s*(实证结果|回归结果|基准回归|主要结果)",
                   r"(4|5)[、．.]\s*(实证|回归|结果)",
                   r"empirical results", r"baseline results"]),
    ("robust",    [r"(五|六)[、．.]\s*(稳健性|进一步分析|拓展分析)",
                   r"(5|6)[、．.]\s*(稳健性|robustness)",
                   r"robustness"]),
    ("conclusion",[r"(五|六|七)[、．.]\s*(结论|结语|总结)",
                   r"(5|6|7)[、．.]\s*(结论|conclusion)",
                   r"^结论$", r"conclusion"]),
]

MAX_SECTION_CHARS = 6000   # 每段最多送给AI的字符数
MAX_FULL_CHARS    = 18000  # 全文摘要模式上限


def extract_pages(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [page.get_text() for page in doc]


def clean(text: str) -> str:
    # 保留换行结构，只压缩连续空格
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def split_sections(pages: list[str]) -> dict[str, str]:
    """
    尝试按章节标题切分论文，返回 {section_key: text} 字典。
    若切分失败，退回到按页数比例划分。
    """
    full_text = clean("\n".join(pages))
    sections = {}

    # 找每个章节的起始位置
    found = []
    for key, patterns in SECTION_PATTERNS:
        for pat in patterns:
            m = re.search(pat, full_text, re.IGNORECASE | re.MULTILINE)
            if m:
                found.append((m.start(), key))
                break

    found.sort()

    if len(found) >= 3:
        for i, (start, key) in enumerate(found):
            end = found[i + 1][0] if i + 1 < len(found) else len(full_text)
            sections[key] = full_text[start:end][:MAX_SECTION_CHARS]
    else:
        # 退回：前10%摘要+引言，中间60%正文，后30%稳健+结论
        n = len(full_text)
        sections["intro"]   = full_text[:int(n * 0.15)][:MAX_SECTION_CHARS]
        sections["design"]  = full_text[int(n * 0.15):int(n * 0.55)][:MAX_SECTION_CHARS]
        sections["results"] = full_text[int(n * 0.55):int(n * 0.80)][:MAX_SECTION_CHARS]
        sections["robust"]  = full_text[int(n * 0.80):][:MAX_SECTION_CHARS]

    return sections


def get_full_text(pages: list[str], max_chars: int = MAX_FULL_CHARS) -> str:
    return clean("\n".join(pages))[:max_chars]


def get_meta(pages: list[str]) -> dict:
    """提取标题、作者等基本信息（取前1.5页）"""
    head = clean("\n".join(pages[:2]))[:800]
    return {"head": head}


class PaperReader:

    def __init__(self, pdf_bytes: bytes):
        self.pages    = extract_pages(pdf_bytes)
        self.sections = split_sections(self.pages)
        self.full     = get_full_text(self.pages)
        self.meta     = get_meta(self.pages)

    def get_context_for_review(self) -> str:
        """
        生成送给审稿人AI的完整论文上下文。
        拼接顺序：摘要→引言→研究设计→实证结果→稳健性→结论
        """
        order = ["abstract", "intro", "literature", "design", "results", "robust", "conclusion"]
        parts = []
        for key in order:
            if key in self.sections:
                label = {
                    "abstract":   "【摘要】",
                    "intro":      "【引言】",
                    "literature": "【文献与假设】",
                    "design":     "【研究设计】",
                    "results":    "【实证结果】",
                    "robust":     "【稳健性分析】",
                    "conclusion": "【结论】",
                }.get(key, f"【{key}】")
                parts.append(f"{label}\n{self.sections[key]}")
        return "\n\n".join(parts) if parts else self.full

    def summary_stats(self) -> dict:
        total_chars = sum(len(p) for p in self.pages)
        return {
            "pages":       len(self.pages),
            "chars":       total_chars,
            "sections":    list(self.sections.keys()),
        }
