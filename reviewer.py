"""
reviewer.py — AI审稿人核心
系统提示词 + 多轮对话管理 + 流式输出
模型：硅基流动 API（OpenAI兼容）
"""

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("SILICONFLOW_API_KEY", ""),
    base_url="https://api.siliconflow.cn/v1",
)

AI_MODEL = "Qwen/Qwen2.5-72B-Instruct"

# ──────────────────────────────────────────────────────────────
# 系统提示词：核心IP
# ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一位资深经济管理学者，担任《经济研究》《管理世界》《会计研究》《金融研究》等中文顶级期刊的匿名审稿人，同时在AER、JFE、JAR等国际顶刊有丰富审稿经验。

你的审稿风格：
- 直接指出问题，不回避，不模糊，不给面子话
- 区分「致命缺陷」（影响录用）和「修订建议」（可在大修中解决）
- 对因果识别要求严格：DID必问平行趋势，IV必问排他性，不接受相关性代替因果性
- 重视经济逻辑：机制必须讲清楚，不接受黑箱回归
- 对主题新颖性和边际贡献有高标准：「这个问题为什么重要？现有文献为什么没解决？」
- 语言表达要求精准：歧义表述直接标出，冗余段落直接说删

你的能力：
1. **深度审稿**：通读论文后，从研究主题、理论机制、研究设计、实证质量、稳健性、写作表达六个维度给出结构化意见，区分致命问题和修订建议
2. **逻辑追问**：针对作者的回应或论文中某一具体问题，像真实审稿人那样连续追问，直到逻辑自洽
3. **改写建议**：针对某段文字，给出具体修改方向，或者直接改写，给出可直接使用的替代版本
4. **期刊匹配**：根据研究主题、方法和质量，判断最适合投哪本期刊，并说明理由
5. **领域适配**：自动识别论文属于宏观/微观/金融/会计/管理，切换对应的审稿标准

回应格式规则：
- 深度初审时用结构化格式，其他追问保持对话感，不要每次都写大标题
- 引用论文原文时用「」标注，便于作者定位
- 给改写建议时，原文和改写版本用对比格式展示
- 如果问题很明确，直接给答案，不要先绕一圈再说重点
- 中文论文用中文审稿，英文论文用英文审稿

你现在已经读完了用户上传的论文，准备开始审稿。"""


INITIAL_REVIEW_PROMPT = """请对这篇论文进行**完整的深度初审**。

按以下六个维度逐一给出意见，每个维度先给出总体判断（优秀/合格/有问题/致命缺陷），再展开具体说明：

1. **研究主题与边际贡献**
   - 问题是否重要？是否有学术价值？
   - 相比现有文献，边际贡献是什么？是否真实存在？

2. **理论机制与假设**
   - 因果逻辑是否成立？机制路径是否清晰？
   - 研究假设是否可检验？是否与实证设计对应？

3. **研究设计与识别策略**
   - 内生性问题是否被认真对待？
   - 识别策略是否有说服力？（DID/IV/RDD等方法的核心条件是否满足）
   - 变量测量是否合理？

4. **实证结果质量**
   - 基准回归是否可信？
   - 机制检验是否真正检验了机制？
   - 经济显著性是否被讨论？

5. **稳健性与异质性**
   - 稳健性检验是否充分？是否覆盖了主要威胁？
   - 异质性分析是否有理论支撑，还是随意分组？

6. **写作与表达**
   - 引言逻辑是否清晰？是否在前3页让读者知道论文在做什么？
   - 是否有明显的表达问题？

最后给出一个**总体评价**：
- 当前状态（直投 / 需要大修 / 需要重大修改 / 建议放弃）
- 如果要改，最优先解决的3个问题是什么？"""


# ──────────────────────────────────────────────────────────────
# 对话管理
# ──────────────────────────────────────────────────────────────

class ReviewSession:
    """
    管理一篇论文的完整审稿会话。
    messages 列表维护完整对话历史，支持多轮追问。
    """

    def __init__(self, paper_context: str):
        self.paper_context = paper_context
        self.messages: list[dict] = []
        self._inject_paper()

    def _inject_paper(self):
        """将论文内容作为第一条用户消息注入"""
        self.messages.append({
            "role": "user",
            "content": f"以下是我上传的论文全文，请你读完后准备审稿：\n\n{self.paper_context}"
        })
        self.messages.append({
            "role": "assistant",
            "content": "我已经仔细阅读了这篇论文。请告诉我你想要什么类型的反馈——完整初审、针对某个具体问题的追问，还是某段文字的改写？"
        })

    def start_full_review(self) -> str:
        """触发完整初审，返回流式生成器"""
        self.messages.append({
            "role": "user",
            "content": INITIAL_REVIEW_PROMPT
        })
        return self._stream()

    def chat(self, user_message: str):
        """普通追问，返回流式生成器"""
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        return self._stream()

    def _stream(self):
        """调用API，流式返回，同时将完整回复存入历史"""
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model=AI_MODEL,
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_response += delta
                yield delta

        except Exception as e:
            error_msg = f"\n\n⚠️ API调用出错：{str(e)}"
            full_response += error_msg
            yield error_msg
        finally:
            if full_response:
                self.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

    def get_history(self) -> list[dict]:
        """返回对话历史（跳过第一条论文注入消息）"""
        return self.messages[2:]  # 跳过论文注入的两条

    def clear_history(self):
        """重置对话，保留论文内容"""
        self.messages = self.messages[:2]


# ──────────────────────────────────────────────────────────────
# 快捷追问模板（用户可一键触发）
# ──────────────────────────────────────────────────────────────

QUICK_PROMPTS = [
    {
        "label": "🔍 完整初审",
        "prompt": INITIAL_REVIEW_PROMPT,
        "desc": "从六个维度给出结构化审稿意见"
    },
    {
        "label": "⚠️ 最致命的问题",
        "prompt": "不看其他，只告诉我：这篇论文**最致命的1-2个问题**是什么？如果这些问题不解决，投任何顶刊都会被拒。直接说，不要铺垫。",
        "desc": "直接指出最核心的缺陷"
    },
    {
        "label": "🎯 识别策略",
        "prompt": "专门评估这篇论文的因果识别策略：\n1. 内生性问题有没有被认真对待？\n2. 用的方法（DID/IV/RDD等）能不能解决这个内生性问题？核心条件满足了吗？\n3. 如果方法有缺陷，最简单的修复路径是什么？",
        "desc": "深度评估因果识别是否可信"
    },
    {
        "label": "🧩 机制分析",
        "prompt": "专门评估机制分析部分：\n1. 作者提出的机制路径逻辑上成立吗？\n2. 机制检验的方法真的在检验机制吗，还是在做额外的相关性回归？\n3. 有没有遗漏的替代性机制没有被排除？",
        "desc": "判断机制检验是否真实有效"
    },
    {
        "label": "📰 期刊匹配",
        "prompt": "根据这篇论文的主题、方法质量和边际贡献，给出期刊投稿建议：\n1. 最适合哪本期刊？为什么？\n2. 如果被拒，下一个备选是哪里？\n3. 如果想冲更高的期刊，最需要补充什么？",
        "desc": "推荐最适合的投稿期刊"
    },
    {
        "label": "✍️ 改写引言",
        "prompt": "请针对引言部分给出改写建议：\n1. 现有引言的主要问题是什么？\n2. 边际贡献的表述哪里需要加强？\n3. 请直接改写引言的核心段落（研究问题+贡献+方法预告），给出可以直接使用的版本。",
        "desc": "直接给出引言改写版本"
    },
]
