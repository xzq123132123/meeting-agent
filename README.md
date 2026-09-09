# 智纪 · 会议纪要 & 周报智能体

实习项目：多模态输入 → 结构化会议纪要 → 可视化周报 → Word 导出。
基于 Streamlit + LLM（OpenAI 兼容接口）。

## 快速启动

```bash
# 方式一：双击（推荐）
start.bat

# 方式二：命令行
D:\ancacoda\python.exe -m streamlit run app.py
```

启动后浏览器访问 http://localhost:8501

> `start.bat` 会自动完成：查找 Python（优先本机 Anaconda，其次 PATH 中的 python）→ 检查依赖 → 缺依赖自动安装 → 启动应用。

## 把项目发给别人用

对方需要先满足一个条件：**安装了 Python 3.10+**（装 Python 时勾选 "Add python.exe to PATH"）。

拿到整个 `meeting-agent` 文件夹后，双击 `start.bat` 即可（会自动装依赖并启动）。若对方没有 Python，请其到 https://www.python.org/downloads/ 安装，或直接把**本机演示录屏**发过去。

> 注意：`start.bat` 里优先使用本机 Anaconda 路径（`D:\ancacoda\python.exe`），对方机器不存在该路径时会自动改用其 PATH 中的 python，无需修改脚本。

## 项目结构

```
meeting-agent/
├── app.py              # Streamlit 主界面（炫酷暗色主题）
├── start.bat           # Windows 一键启动脚本
├── sample_data.py      # 内置演示数据（离线兜底，含模拟语音转写）
├── requirements.txt    # 依赖清单
├── core/
│   ├── asr.py          # 语音转写（OpenAI 兼容，multipart→chat 自动降级）
│   ├── llm.py          # LLM 调用（OpenAI 兼容，JSON 容错解析、自动重试、配置防呆）
│   ├── parser.py       # 文本清洗 / txt·docx·md·csv 解析 / 长文本分块
│   ├── prompts.py      # 纪要 & 周报提示词工程
│   ├── report.py       # 多份纪要聚合统计、周报正文生成
│   └── export.py       # Word（.docx）导出：纪要、周报
└── tests/
    ├── test_core.py    # 核心模块单元测试
    ├── test_app.py     # AppTest 页面级全流程测试（含语音、去重）
    ├── test_asr.py     # 语音转写降级逻辑测试（mock 网络）
    └── test_llm_config.py # API 配置防呆校验测试
```

## 功能说明

| 模块 | 说明 |
|---|---|
| 多模态输入 | 粘贴文本 / 上传文件（txt·md·csv·log·docx）/ **上传语音（自动转写）** / 一键载入示例 |
| 语音转写 | 上传 wav·mp3·m4a·flac·ogg·aac 录音 → 自动转文字 → 直接分析（通义 qwen3-asr-flash / OpenAI whisper 通用，自动降级） |
| 内容去重 | 同一内容只分析一次，重复点击会提示，避免纪要重复生成 |
| 智能纪要 | 议题拆分、要点提炼、结论/决策抽取 |
| 待办清单 | 任务 + 负责人 + 截止时间 + 优先级（高/中/低着色） |
| 风险提醒 | 自动识别风险项 |
| 一键周报 | 多场会议聚合：任务分布柱状图、优先级占比饼图、周报正文 |
| **智能问答** | 对纪要连续追问（多轮对话）：提取任务、按人分组、任意提问 |
| **多形态输出** | 一键生成：英文纪要 / PPT 大纲 / 汇报邮件 / 高优待办清单 / 一句话总结 |
| Word / txt 导出 | 纪要、周报可下载 .docx；问答记录可导出 txt |

## 配置模型（两种模式）

1. **示例模式**（默认开启，无需 Key）：使用内置数据即时演示，离线可用。
2. **真实模式**：在左侧边栏关闭示例模式，然后：
   - **模型服务商**：下拉选择（通义千问 / 豆包方舟 / DeepSeek / OpenAI / 智谱），Base URL 自动填入；
   - **API Key**：填你的密钥（通义千问为 `sk-` 开头）；
   - **模型名称**：填模型名（通义千问如 `qwen-plus` / `qwen-turbo` / `qwen-max`；豆包方舟填控制台 Model ID）。

   常见服务商参数：
   | 服务商 | Base URL | 模型示例 |
   |---|---|---|
   | 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-plus / qwen-turbo / qwen-max |
   | 豆包方舟 | `https://ark.cn-beijing.volces.com/api/v3` | doubao-seed-1-6-251015（控制台查） |
   | DeepSeek | `https://api.deepseek.com` | deepseek-chat |
   | OpenAI | `https://api.openai.com/v1` | gpt-4o-mini |
   | 智谱 | `https://open.bigmodel.cn/api/paas/v4` | glm-4-flash |

## 3 分钟演示脚本

1. **语音路线**：切到「🎙 上传语音」→ 示例模式点「转写为文字」（模拟转写）→「开始智能分析」→ 展示纪要；
2. 再「载入示例 · 群聊记录」→「开始智能分析」→ 生成第 2 份纪要（同一内容重复点击不会重复生成，会提示去重）；
3. 点击「生成周报」→ 展示统计图表 + 周报正文 → 下载 Word；
4. **智能问答**：点「PPT 大纲」一键出汇报大纲 → 再输入"翻译成英文"→ 输出英文纪要 → 「导出对话记录」。

## 已通过验证

- `tests/test_core.py`：清洗/分块/聚合/周报/Word 导出/JSON 容错解析 全部通过
- `tests/test_app.py`：AppTest 模拟完整操作（语音转写→分析→清空→示例→去重→周报→下载）全部通过
- `tests/test_asr.py`：语音转写 multipart/chat 降级逻辑（mock 网络）全部通过
- `tests/test_llm_config.py`：API 配置防呆校验（中文/全角/换行/emoji 误粘贴检测）全部通过
- 服务启动 HTTP 200，无运行时异常

## 常见问题

- **语音转写失败**：确认侧边栏已填 API Key、展开「语音转写配置」确认 ASR 模型（通义默认 `qwen3-asr-flash`）；两种调用方式会自动降级尝试；
- **404 InvalidEndpointOrModel**：模型名填错或未开通，检查「模型名称」框（别把 Key 填进去）；
- **latin-1 codec 报错**：某个配置框里粘贴了中文/换行/特殊符号，应用会自动检测并提示位置；
- **接口报 401**：API Key 无效，检查配置；
- **接口报 429**：触发限流，代码已自动重试 2 次，稍后再试；
- **长文本**：超过 8000 字自动分块处理并合并结果；
- **换电脑部署**：`pip install -r requirements.txt` 后即可运行。
