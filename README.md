# 题目提取工具

从试卷 PDF 中自动提取题目，生成结构化 JSON，供题库/Bot 使用。**当前仍在测试阶段。**

使用**视觉语言模型 (VLM) API** 直接"看"试卷图片，一步完成文字识别、版面理解、题型分类。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置 API Key
export API_KEY="sk-xxx"

# 3. 运行
python main.py 试卷.pdf
```

## 支持的 API 厂商

设置环境变量即可切换：

| 厂商 | API_BASE_URL | 推荐模型 |
|------|-------------|---------|
| 阿里百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-max` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v` |
| 自定义 | 任意 OpenAI 兼容地址 | — |

```bash
# 阿里百炼（默认）
export API_KEY="sk-xxx"
python main.py exam.pdf

# OpenAI
export API_KEY="sk-xxx"
export API_BASE_URL="https://api.openai.com/v1"
python main.py exam.pdf --model gpt-4o

# 自定义接口
python main.py exam.pdf \
  --api-key "sk-xxx" \
  --api-base "https://your-api.com/v1" \
  --model "your-model"
```

## 命令行参数

```
python main.py 试卷.pdf [选项]

  -s, --subject     科目名称（如: 化学、物理）
  -o, --output      输出 JSON 路径（默认: output/questions.json）
  --bot-db          Bot 数据库输出路径
  --model           模型名称（默认: qwen-vl-max）
  --api-key         API Key
  --api-base        API Base URL
  --dpi             PDF 渲染分辨率（默认: 200）
  --max-tokens      单次最大输出 token（默认: 8192）
  -c, --config      配置文件路径（默认: config.yaml）
```

## 输出格式

### questions.json

```json
{
  "source": {"file": "exam.pdf", "subject": "化学"},
  "metadata": {"total": 40, "type_stats": {"single_choice": 16}},
  "questions": [
    {
      "id": 1,
      "type": "single_choice",
      "type_cn": "单选题",
      "content": "化学与生活...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "answer": "D"
    }
  ]
}
```

### bot_db.json (Bot 数据库格式)

```json
{
  "version": "4.0",
  "total": 40,
  "entries": [
    {
      "id": "Q0001",
      "type": "single_choice",
      "content": "化学与生活...",
      "options": ["A. ...", "B. ..."],
      "answer": "D",
      "keywords": ["化学", "生活", "科技"]
    }
  ]
}
```


## 项目结构

```
├── main.py              # 入口
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖
├── src/
│   ├── pdf_processor.py # PDF → 图片
│   ├── api_extractor.py # VLM API 提取
│   └── output_formatter.py # JSON 输出
└── output/              # 生成结果（自动创建）
```

## License

MIT
