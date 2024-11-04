### README 文件

```markdown
# Emby 视频处理脚本

## 概述

本文件夹包含用于 Emby 视频处理的脚本。这些脚本主要用于自动化视频文件的元数据处理，确保视频文件在 Emby 媒体服务器中能够正确显示和管理。目前，文件夹中包含的脚本如下：

- `copy_files.py`：用于将刮削后的元数据文件复制到指定的目标文件夹，并根据配置进行过滤和处理。

## 安装

1. **安装 Python**：
   - 确保你的系统已安装 Python 3.6 或更高版本。
   - 你可以从 [Python 官方网站](https://www.python.org/) 下载并安装 Python。

2. **安装依赖**：
   - 本脚本没有外部依赖，只需要 Python 标准库即可运行。

## 使用

### 1. `copy_files.py` 脚本

#### 配置文件

本脚本使用 `config.json` 文件进行配置。请确保 `config.json` 文件的格式正确。以下是一个示例配置文件：

```json
{
    "folder_pairs": [
        {
            "src_folder": "X:\\Source\\电影",
            "dst_folder": "Z:\\Destination\\媒体\\电影"
        },
        {
            "src_folder": "X:\\Source\\动漫",
            "dst_folder": "Z:\\Destination\\媒体\\动漫"
        },
        {
            "src_folder": "X:\\Source\\电视剧",
            "dst_folder": "Z:\\Destination\\媒体\\电视剧"
        },
        {
            "src_folder": "X:\\Source\\剧场版",
            "dst_folder": "Z:\\Destination\\媒体\\剧场版"
        }
    ],
    "exclude_exts": [".avi", ".mkv"],
    "max_size_mb": 100,
    "on_duplicate": "overwrite",
    "log_level": "INFO"
}
```

#### 配置参数说明

- `folder_pairs`：源文件夹和目标文件夹的配对列表。
  - `src_folder`：源文件夹路径。
  - `dst_folder`：目标文件夹路径。
- `exclude_exts`：要排除的文件扩展名列表。
- `max_size_mb`：文件的最大大小（以 MB 为单位）。
- `on_duplicate`：当目标文件夹中存在同名文件时的行为，可选值为 `skip` 或 `overwrite`。
- `log_level`：日志级别，可选值为 `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。

#### 运行脚本

在命令行中运行以下命令来执行脚本：

```sh
python C:\Path\To\Your\Script\copy_files.py
```

### 2. 日志

脚本会根据配置文件中的 `log_level` 设置生成日志。日志会输出到控制台，方便你跟踪脚本的运行情况。

## 常见问题

### 1. 配置文件格式错误

确保 `config.json` 文件的格式正确，特别是注意以下几点：
- 属性名和字符串值必须用双引号 `"` 包围。
- 确保没有多余的逗号。
- 确保 JSON 文件的结构正确。

### 2. 文件路径错误

确保所有配置的文件路径在你的系统中是存在的，并且没有拼写错误。

### 3. 日志输出不正确

检查配置文件中的 `log_level` 设置是否正确。如果设置为 `DEBUG`，你会看到更多的调试信息。

## 联系

如果在使用过程中遇到问题或有任何建议，请联系 [hope140@outlook.com]。
