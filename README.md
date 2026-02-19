# OpenCut - 旅游视频全自动剪辑系统

> 专为旅游博主设计的 AI 剪辑助手。8TB 素材全自动管理、剧本自适应、一键成片。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FFmpeg](https://img.shields.io/badge/ffmpeg-4.0+-green.svg)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 项目愿景

**让任何人都能在 10 分钟内，用自己的素材剪出电影感旅游视频。**

- ✅ 8TB 素材全自动索引（指纹去重 + 语义搜索）
- ✅ 剧本自适应重写（素材不够时自动改戏）
- ✅ 全自动渲染（磨皮/调色/字幕/对拍）
- ✅ 三级哨位确认（你只管点确认，剩下的交给 AI）

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  8TB 素材库 (百度云/Google Drive/本地)                        │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────┐
│  🗂️ Asset Indexer            │  ← 指纹去重 + CLIP 语义索引
│  • fingerprint_scanner       │     快速定位最佳素材
│  • semantic_search           │
└──────────────┬───────────────┘
               │ 返回 Top-K 素材
               ▼
┌──────────────────────────────┐
│  🎬 Script Engine            │  ← 剧本自适应重写
│  • adaptive_rewriter         │     素材不足时自动改文案
│  • emotion_curve             │
└──────────────┬───────────────┘
               │ 三级哨位确认
               ▼
┌──────────────────────────────┐
│  🎨 Render Pipeline          │  ← 全自动渲染
│  • beauty_filter (磨皮)      │     MediaPipe + FFmpeg
│  • color_grading (调色)      │     YUV 肤色保护
│  • subtitle_burn (字幕)      │     Whisper + 双语
│  • beat_sync (对拍)          │     BPM 锚点
└──────────────┬───────────────┘
               │
               ▼
           📹 成片输出
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/opencut.git
cd opencut

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 FFmpeg (必需)
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html
```

### 2. 配置

```bash
# 复制配置模板
cp config.example.json config.json

# 编辑 config.json
{
  "storage": {
    "type": "local",  // 或 "google_drive", "baiduyun"
    "path": "/path/to/your/8tb/videos"
  },
  "models": {
    "clip_model": "openai/clip-vit-base-patch32",
    "whisper_model": "base",  // faster-whisper
    "sovits_model": "path/to/your/voice.pth"  // 可选，声纹克隆
  },
  "render": {
    "beauty_intensity": 0.7,      // 磨皮强度 0-1
    "lut_preset": "wanderlust",   // 调色风格
    "output_resolution": [1080, 1920],  // 9:16
    "beat_sync": true             // 是否启用 BPM 对拍
  }
}
```

### 3. 第一步：建立素材索引（一次性）

```bash
# 扫描 8TB 素材，建立指纹 + 语义索引
python -m opencut.indexer scan \
  --input /path/to/videos \
  --output ./index/

# 输出：
# • fingerprints.db  (去重数据库)
# • semantic_index.json  (CLIP 语义向量)
```

### 4. 第二步：全自动剪辑

```bash
# 输入你的主题，系统自动完成一切
python -m opencut.editor create \
  --topic "格鲁吉亚山顶的日落" \
  --style "清冷流浪感" \
  --music "lofi-chill" \
  --output ./output/

# 系统会依次执行：
# 1. 语义搜索匹配素材
# 2. 剧本自适应重写（如果素材不够）
# 3. 三级哨位确认（Discord/CLI 交互）
# 4. 全自动渲染（磨皮/调色/字幕/对拍）
```

---

## 📋 核心功能详解

### 🗂️ Asset Indexer - 智能素材管理

**问题**：8TB 素材如何快速找到"格鲁吉亚山顶日落"的那 3 秒？

**解决方案**：

```python
from opencut.indexer import AssetIndex

# 初始化索引
index = AssetIndex.load("./index/")

# 语义搜索
results = index.search(
    query="格鲁吉亚 山顶 日落 人物",
    top_k=5,
    min_duration=3.0
)

# 返回结构化数据
[
  {
    "clip_id": "abc123",
    "file_path": "/videos/georgia/dji_001.mp4",
    "time_range": [120.5, 125.0],
    "similarity_score": 0.87,
    "visual_tags": ["sunset", "mountain", "person"],
    "quality_score": 0.92
  }
]
```

**技术细节**：
- **指纹去重**：Perceptual Hash (pHash) 检测重复/相似片段
- **语义索引**：CLIP 模型提取 512 维视觉特征
- **增量更新**：新增素材时只计算新文件，无需重扫 8TB

---

### 🎬 Script Engine - 剧本自适应

**问题**：剧本写"在雪地里奔跑"，但素材只有"走路"怎么办？

**解决方案**：

```python
from opencut.script import AdaptiveScript

script = AdaptiveScript(
    original="我在雪地里奔跑，感受自由的风",
    required_visual=["snow", "running", "person"]
)

# 当素材匹配度 < 0.6 时自动重写
if best_match.score < 0.6:
    new_script = script.rewrite(
        available_tags=["snow", "walking", "person"],
        emotion="nostalgic"
    )
    # 输出: "我在雪地里漫步，任思绪随风飘散"
```

**三级哨位确认流**：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  哨位 1      │ -> │  哨位 2      │ -> │  哨位 3      │
│ 剧本确认     │    │ 素材修正     │    │ 样片确认     │
├─────────────┤    ├─────────────┤    ├─────────────┤
│ • 文案       │    │ • 平替对比   │    │ • 15s 样片  │
│ • 情绪曲线   │    │ • 预览图     │    │ • 磨皮/调色 │
│ • 音乐选型   │    │ • 10min超时  │    │ • 最终确认  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

### 🎨 Render Pipeline - 全自动渲染

#### 1. 智能磨皮 (Beauty Filter)

```python
from opencut.render import BeautyFilter

# MediaPipe 人脸检测 + 频率分解
filter = BeautyFilter(
    method="frequency_separation",
    skin_smooth_sigma=1.5,
    preserve_features=["eyes", "eyebrows", "lips"]  # 保护五官细节
)

# 只对皮肤区域进行平滑，保留纹理
output = filter.apply(input_frame)
```

#### 2. 肤色保护调色 (Color Grading)

```python
from opencut.render import ColorGrading

grading = ColorGrading(
    lut_preset="wanderlust",      # 清冷低饱和风格
    skin_tone_protection=True,    # YUV 肤色空间锁定
    skin_tone_range={"cb": [77, 127], "cr": [133, 173]}
)

# 背景套用电影感 LUT，肤色保持自然
output = grading.apply(input_frame)
```

#### 3. 中英双语字幕 (Bilingual Subtitles)

```python
from opencut.render import SubtitleEngine

engine = SubtitleEngine(
    whisper_model="faster-whisper-base",
    font="Noto Sans CJK SC",
    style="movie_caption"  # 电影感样式
)

# 自动识别旁白 -> 翻译 -> 压制
engine.generate(
    audio_path="voiceover.wav",
    cn_text="旅行的意义",
    style={"outline": 2, "margin_v": 60}
)
```

#### 4. BPM 对拍 (Beat Sync)

```python
from opencut.render import BeatSync

sync = BeatSync(
    bpm_detection="librosa",
    alignment="peak",  # 对齐鼓点峰值
    tolerance_frames=3  # 容错 3 帧
)

# 自动调整片段入出点
aligned_clips = sync.align(clips, music_path="bgm.mp3")
```

---

## 🛠️ 进阶用法

### 批量处理

```bash
# 批量生成多个主题
python -m opencut.batch \
  --topics topics.txt \
  --template "wanderlust" \
  --output ./batch_output/
```

### 自定义 LUT

```bash
# 添加你自己的调色预设
python -m opencut.lut add \
  --name "my_style" \
  --cube ./my_style.cube \
  --description "我的专属流浪感"
```

### API 模式

```python
from opencut import OpenCutPipeline

pipeline = OpenCutPipeline(config="./config.json")

# 一键执行全流程
video = pipeline.create(
    topic="冰岛黑沙滩的孤独",
    materials_index="./index/",
    confirm_mode="auto"  # 或 "interactive" 启用哨位确认
)

print(f"成片已生成: {video.path}")
```

---

## 📁 项目结构

```
opencut/
├── README.md
├── requirements.txt
├── config.example.json
├── opencut/
│   ├── __init__.py
│   ├── indexer/              # 素材索引
│   │   ├── fingerprint.py    # 视频指纹
│   │   ├── semantic.py       # CLIP 语义索引
│   │   └── search.py         # 多维度搜索
│   ├── script/               # 剧本引擎
│   │   ├── adaptive.py       # 自适应重写
│   │   ├── emotion.py        # 情绪曲线
│   │   └── confirmation.py   # 哨位确认流
│   ├── render/               # 渲染管道
│   │   ├── beauty.py         # 磨皮
│   │   ├── color.py          # 调色
│   │   ├── subtitle.py       # 字幕
│   │   └── sync.py           # BPM 对拍
│   └── editor.py             # 主编辑器
├── tests/                    # 测试用例
├── examples/                 # 示例脚本
└── docs/                     # 详细文档
```

---

## 🧪 测试

```bash
# 运行单元测试
pytest tests/

# 运行集成测试（需要测试视频）
pytest tests/integration/ --videos ./test_videos/
```

---

## 🤝 贡献指南

欢迎 PR！请遵循以下流程：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [FFmpeg](https://ffmpeg.org/) - 视频处理引擎
- [OpenAI CLIP](https://github.com/openai/CLIP) - 语义理解
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - 语音识别
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) - 声音克隆

---

**Made with ❤️ for travelers who want to tell their stories.**
