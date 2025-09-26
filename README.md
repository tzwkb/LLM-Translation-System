# 🎯 LLMTS - 双语平行翻译工具

高效的Excel双语翻译工具，支持术语库、断点续传、详细处理过程展示。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 准备文件
```
📁 input/        # 将待翻译的Excel文件放这里
📁 terminology/  # 将术语库文件放这里（可选）
```

### 3. 运行翻译
```bash
python translator.py
```

### 4. 查看结果
```
📁 output/       # 翻译结果文件
📁 cache/        # 缓存和检查点文件
```

## ✨ 主要特性

- 🌐 **智能翻译**: 支持OpenAI API翻译
- 📚 **术语库**: 专业术语预处理和替换
- 💾 **断点续传**: 中断后可继续翻译
- 🔍 **详细模式**: 完整的处理过程展示
- 📁 **文件管理**: 自动文件分类和路径管理
- ⚡ **高性能**: 智能缓存和批量处理
- 🛠️ **模块化**: 清晰的架构设计

## 📋 支持格式

- **输入**: Excel文件 (.xlsx, .xls)
- **输出**: Excel文件 (.xlsx)
- **术语库**: Excel文件 (中文术语 | 英文术语)

## ⚙️ 配置

API配置已预设，如需修改请编辑 `config_manager.py`:

```python
@dataclass
class TranslationConfig:
    api_key: str = 'your-api-key'
    base_url: str = 'https://api.ai-gaochao.cn/v1'
    model: str = 'gpt-4o'
```

## 📚 详细文档

参见 `ENGINEERING_GUIDE.md` 了解完整的使用指南和开发文档。

## 🏗️ 架构

```
translator.py           # 主程序入口
├── config_manager.py   # 配置管理
├── file_manager.py     # 文件管理
├── translation_engine.py # 翻译引擎
└── checkpoint_manager.py # 检查点管理
```

## 📄 许可证

本项目采用 MIT 许可证。