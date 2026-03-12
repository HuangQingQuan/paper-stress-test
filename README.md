# 实证研究 AI Co-Pilot — MVP

基于 Streamlit + 硅基流动（DeepSeek-V3）的实证研究协作系统。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用
streamlit run app.py
```

浏览器自动打开 http://localhost:8501

## 使用流程

### 准备
1. 前往 https://cloud.siliconflow.cn 获取 API Key
2. 在侧边栏粘贴 API Key

### 阶段二：识别策略 & 预登记（Tab 1）
1. 输入研究问题，点击"AI 生成方案"
2. 从 3-4 个策略中选择一项（人类拍板）
3. 填写规格列表（因变量、自变量、控制变量等）
4. 勾选确认后锁定——**此步骤不可逆，是系统核心闸门**

### 阶段三：执行流水线（Tab 2）
1. 上传 CSV 数据集（或使用内置演示数据）
2. 查看数据质量诊断报告
3. 点击执行——系统将按预登记规格跑 Baseline + 稳健性

### 阶段四：异常诊断（Tab 3）
1. 点击"运行自动异常检测"
2. 对每个异常进行人类判断（数据问题 / 真实机制 / 需调查）
3. 若需回滚，返回 Tab 1 重新登记
4. 可生成 AI 结果解释草稿（需人工审阅因果语言）

## 审计日志
- 所有操作自动记录在侧边栏
- 支持一键导出完整日志 .txt 文件

## 后续扩展方向
- [ ] 阶段一：AI 文献缺口报告（+ DOI 强制核验）
- [ ] 阶段五：因果语言自动检测 Agent
- [ ] 多代理错误隔离机制
- [ ] 跨会话持久化存储（SQLite）
- [ ] Stata/R 代码生成导出

## 依赖说明
- **硅基流动 API**：兼容 OpenAI 格式，模型 `deepseek-ai/DeepSeek-V3`
- **statsmodels**：OLS 回归执行（HC3 稳健标准误）
- **streamlit**：Web 交互界面
