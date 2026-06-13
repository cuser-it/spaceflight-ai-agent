# 航天任务 AI Agent

一个面向卫星任务查询的中文 AI 助手。应用使用 Streamlit 构建交互界面，结合 DeepSeek 对话能力、Space-Track TLE 数据和 SGP4 轨道计算，在 3D 地球仪上展示卫星当前位置、预测路径和未来位置。

## 功能特性

- 中文自然语言查询，例如：`中国空间站在哪里？`、`预测国际空间站 1 小时后的位置`
- 自动识别轨道相关问题，并调用 Space-Track 获取最新 TLE
- 使用 SGP4 计算卫星经纬度、高度和预测轨迹
- 支持国际空间站、哈勃望远镜、中国空间站等常见卫星名称
- 3D 地球仪视图，固定南北极，展示卫星标记、预测轨迹和状态 HUD
- 右侧中文对话面板，用户消息即时显示，普通 AI 回复支持流式输出
- DeepSeek 未配置时提供本地兜底回复，方便演示基础 UI
- TLE 内存缓存，减少短时间重复请求 Space-Track
- 本地静态资源加载 Three.js 和 WebP 地球贴图，减少首屏 iframe 体积

## 项目结构

```text
satellite_agent/
├── .env.example
├── .streamlit/
│   └── config.toml
├── app.py
├── assets/
│   └── textures/                 # 原始地球贴图
├── static/
│   ├── textures/                 # 首屏使用的轻量 WebP 贴图
│   └── vendor/
│       └── three-r128.min.js     # 本地 Three.js
├── src/
│   ├── agent.py                  # LangGraph/LLM 路由与回复逻辑
│   ├── globe.py                  # Three.js 地球仪组件
│   ├── state.py
│   ├── tools.py                  # Space-Track 查询与 SGP4 计算
│   └── utils.py                  # 时间、TLE、坐标转换工具
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   └── test_tools.py
├── requirements.txt
└── README.md
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

在 `.env` 中填入自己的凭据：

```text
DEEPSEEK_API_KEY=your_deepseek_key
SPACETRACK_USER=your_email@example.com
SPACETRACK_PASS=your_password
```

`DEEPSEEK_API_KEY` 用于开放对话和流式回复。`SPACETRACK_USER`、`SPACETRACK_PASS` 用于查询真实 TLE 数据。不要把 `.env` 提交到仓库。

4. 启动 Web 应用。

```bash
streamlit run app.py
```

默认访问地址：

```text
http://localhost:8501
```

## 使用示例

```text
国际空间站现在在哪里？
中国空间站在哪里？
预测国际空间站 1 小时后的位置
哈勃望远镜 30 分钟后的位置？
ISS 当前坐标是多少？
你能做什么？
```

轨道类问题会进入工具链：解析卫星名称和预测时间，获取 TLE，计算当前位置或未来位置，并更新左侧 3D 地球视图。

## 运行测试

```bash
pytest tests/
```

测试默认不会调用真实 DeepSeek 或 Space-Track API。`tests/test_tools.py` 会验证 TLE 解析、SGP4 计算和工具逻辑；`tests/test_agent.py` 会验证意图路由、回复格式和预测轨迹生成。

## 实现说明

- `app.py` 负责 Streamlit 页面布局、中文 UI、对话区滚动、输入框样式和模型连接状态。
- `src/agent.py` 使用 LangGraph 构建任务流，并延迟到首次用户请求时初始化，减少首屏启动成本。
- `src/tools.py` 负责卫星名称映射、Space-Track TLE 查询、TLE 缓存和 SGP4 位置计算。
- `src/globe.py` 使用 Three.js 渲染地球仪、卫星标记、轨迹线和 HUD 状态。
- `.streamlit/config.toml` 开启 Streamlit 静态资源服务，供 iframe 加载 `/app/static/...` 下的 Three.js 和贴图。
- `static/textures/*.webp` 是首屏使用的轻量贴图；`assets/textures/` 保留较高分辨率原始贴图。

## 注意事项

- Space-Track 账号需要遵守其使用条款和请求频率限制。
- 当前支持的常见名称在 `src/tools.py` 的 `SATELLITE_NAME_TO_NORAD_ID` 中维护。
- 预测轨迹基于当前 TLE 和 SGP4 计算，适合任务演示和近实时估算，不应作为正式任务控制依据。
- 如果部署到远程环境，需要同步配置环境变量，并确保 Streamlit 静态资源服务已启用。
