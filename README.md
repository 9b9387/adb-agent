# ADB Phone Automation Agent

基于 Google ADK + Android ADB 的纯视觉手机自动化代理。Agent 接收任务指令，通过截图分析当前屏幕状态，自动规划并执行 ADB 操作。

## 架构

- **单 LLM Agent**，使用 `gemini-2.5-flash` 视觉模型
- **纯视觉方案**：通过截图感知屏幕，无需 OCR 或无障碍树
- **Agent Loop**：截图注入 → LLM 思考 → 调用 ADB 工具 → 验证结果 → 循环
- **坐标归一化**：Gemini 输出 0-1000 归一化坐标，工具内部自动转换为真实像素

## 环境准备

1. 安装 [uv](https://docs.astral.sh/uv/)
2. 配置 Android ADB 并连接设备：
   ```bash
   adb devices  # 确认设备已连接
   ```
3. 复制环境变量文件并填入 API Key：
   ```bash
   cp .env.example .env
   # 编辑 .env，填入 GOOGLE_API_KEY
   ```
4. 安装依赖：
   ```bash
   uv sync
   ```

## 使用方式

### CLI 方式
```bash
uv run python main.py "打开设置应用"
uv run python main.py "打开微信并发送你好给张三"
```

### ADK Web UI（开发调试）
```bash
uv run adk web
# 浏览器打开 http://localhost:8000，选择 adb_agent
```

## 工具列表

### 屏幕操作
- `get_screen_size` — 获取屏幕分辨率

### 交互操作
- `tap` / `long_press` / `double_tap` — 点击操作（坐标 0-1000）
- `swipe` — 滑动操作
- `type_text` — 文本输入
- `set_clipboard` / `get_clipboard` — 剪贴板操作
- `press_key` / `press_back` / `press_home` / `press_enter` / `press_recent_apps` — 按键
- `open_app` / `close_app` / `clear_app_data` — 应用管理
- `open_url` — 打开链接
- `wait` — 等待

### 文件操作
- `push_file` / `pull_file` — 文件上传/下载
- `list_files` / `delete_file` — 文件列表/删除

### 设备信息
- `get_device_info` — 设备详情
- `get_battery_info` — 电池状态
- `get_current_app` — 当前前台应用
- `get_installed_packages` — 已安装应用列表
- `get_screen_state` / `wake_screen` / `lock_screen` — 屏幕状态管理

## 项目结构

```
adb-agent/
├── pyproject.toml
├── .env.example
├── main.py                 # CLI 入口
├── adb_agent/
│   ├── __init__.py
│   ├── agent.py            # Agent 定义
│   ├── callbacks.py        # before_model_callback（截图注入）
│   ├── prompts.py          # 系统指令
│   └── tools/
│       ├── __init__.py     # ALL_TOOLS 聚合导出
│       ├── screen.py       # 截屏与图像处理
│       ├── actions.py      # 交互操作
│       ├── file_ops.py     # 文件传输
│       └── device_info.py  # 设备信息
└── README.md
```
