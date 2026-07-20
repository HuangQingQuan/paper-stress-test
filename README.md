# 同态待办 · 拍照断舍离原型

一个可直接分享测试的 Streamlit 交互原型：

1. 上传一组家庭闲置物品照片
2. 查看并修改 AI 的“留 / 卖 / 捐 / 扔”建议
3. 生成处理待办，逐项打勾
4. 全部处理后展示一次性完成总结

## 本地启动

```bash
pip install -r requirements.txt
streamlit run app.py
```

打开 `http://localhost:8501`。没有准备照片时，可以在首页选择“先体验一个示例”走完整流程。

## 配置硅基流动视觉模型

在 Streamlit Cloud 的 **Manage app → Settings → Secrets** 中添加：

```toml
SILICONFLOW_API_KEY = "sk-你的密钥"
SILICONFLOW_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
```

`SILICONFLOW_MODEL` 可以省略，应用默认使用上面的视觉模型。本地开发也可使用同名环境变量。

## 原型边界

- 上传的照片会发送给硅基流动视觉模型进行识别与建议；未配置 API Key 时仍可使用内置示例体验流程。
- AI 只给建议，用户可以修改每一件物品的最终决定。
- 用户完成本轮整理后，上传照片会从会话状态中移除，仅保留结构化处理结果。
- 空间数据为体验用途的估算值。
