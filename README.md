# 航天任务 AI Agent

基于 LangGraph 的卫星任务智能助手 demo，支持通过自然语言查询卫星位置，自动获取 TLE，并使用 SGP4 计算实时或预测轨道位置。

## 功能

- 支持中文自然语言交互，例如：`国际空间站现在在哪里？`
- 使用 Space-Track API 获取最新 TLE 数据
- 使用 SGP4 计算卫星经纬度与高度
- 提供 Streamlit 多轮对话界面
- 具备内存缓存，避免短时间重复请求同一颗卫星的 TLE
- 在缺少 DeepSeek Key 时提供本地兜底回复，方便演示 UI

## 项目结构

```text
satellite_agent/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── app.py
├── src/
│   ├── __init__.py
│   ├── agent.py
│   ├── state.py
│   ├── tools.py
│   └── utils.py
└── tests/
    ├── conftest.py
    ├── test_agent.py
    └── test_tools.py
```

## 快速开始

1. 创建并激活虚拟环境。

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖。

```bash
pip install -r requirements.txt
```

3. 配置环境变量。

```bash
cp .env.example .env
```

在 `.env` 中填入：

```text
DEEPSEEK_API_KEY=your_deepseek_key
SPACETRACK_USER=your_email@example.com
SPACETRACK_PASS=your_password
```

4. 运行 Web 界面。

```bash
streamlit run app.py
```

## 使用示例

- `国际空间站现在在哪里？`
- `ISS 当前坐标是多少？`
- `哈勃望远镜 30 分钟后的位置？`
- `你能做什么？`

## 测试

```bash
pytest tests/
```

测试默认不会调用真实 Space-Track 或 DeepSeek API。`test_tools.py` 会在安装 `sgp4` 后验证 TLE 解析与轨道计算；缺少 `sgp4` 时相关用例会跳过。

## 实现说明

- `src/tools.py` 负责卫星名称映射、Space-Track TLE 查询、TLE 缓存和 SGP4 位置计算。
- `src/utils.py` 负责 TLE 行解析、时间解析、GMST 计算和 ECEF 到 WGS84 经纬度转换。
- `src/agent.py` 构建 LangGraph 工作流：先识别意图，再路由到轨道工具或普通对话节点。
- `app.py` 使用 Streamlit 的 chat UI 展示多轮对话。

## 后续优化

- 自动搜索 NORAD ID，减少手工名称映射
- 增加文件或 Redis 缓存，按 TLE epoch 控制刷新
- 增加轨迹地图可视化
- 拆分规划 Agent 和工具执行 Agent
- 部署到 Streamlit Cloud 或 Hugging Face Spaces
