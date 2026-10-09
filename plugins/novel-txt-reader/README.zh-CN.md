# novel-txt-reader（插件）

[English](README.md) | 简体中文 | [仓库中文使用说明](../../README.zh-CN.md)

这是一个可跨宿主使用的代理技能，同时提供 Claude 兼容的插件打包。它将纯文本 `.txt` 小说转换为轻量的**离线 HTML 阅读器**：按章节拆分、统一使用 UTF-8 编码，并支持自动保存阅读位置和手动书签。可在 Claude、Codex 和 DeepSeek Harness（DSH）中使用，也可直接通过 Python 运行。

## 组件

| 组件 | 名称 | 用途 |
| --- | --- | --- |
| 技能 | novel-txt-reader | 严格解码、按章节拆分并生成阅读器页面。 |

## 使用方法

向代理提出请求，例如：

> 用 novel-txt-reader 把这个 TXT 按章节拆分成离线阅读器，输入路径是 `C:\Books\book.txt`，输出到 `C:\Books\reader`。

宿主必须能够访问这些路径。

技能会运行 `scripts/build_reader.py <input.txt> <output_folder>`。这里的脚本路径相对于 `skills/novel-txt-reader/SKILL.md` 所在目录，而不是代理的当前工作目录。生成的输出文件夹包含 `开始阅读.html`（用浏览器打开）、`使用说明.txt`，以及 `data/` 下的章节文件。

## 安装与前提条件

通过 Claude 或兼容的 Codex 插件市场安装插件，或将整个 `skills/novel-txt-reader` 文件夹复制到宿主支持的技能根目录。Codex 与 DSH 可以共用 `~/.agents/skills/novel-txt-reader`；DSH 也支持 `~/.dsh/skills/novel-txt-reader`。DSH 通过技能发现机制加载本技能，不会安装 `.claude-plugin/plugin.json`。请保留技能文件夹内 `scripts/` 中的 Python 文件和 HTML 模板。

完整源码仓库中的[兼容性与安装说明](../../COMPATIBILITY.zh-CN.md)提供了具体步骤、官方资料和验证范围。转换需要 Python 3、shell 命令执行能力、输入文件的读取权限和输出目录的写入权限。转换器本身不需要凭据或第三方 Python 包；代理宿主可能有自己的登录要求。生成后只需浏览器即可阅读。

如果源文件的编码存在歧义，需要明确指定编码，例如 `--encoding big5`；遇到无法解码的字节时会停止转换，不会静默替换为其他字符。

尚未发布的 0.1.2 增加了阅读进度导入校验、按书籍隔离进度、保留普通正文与输出目录中的无关文件，并在通常的重新生成失败情形下保护现有阅读器。重新生成旧版阅读器前，请先备份阅读进度；迁移旧版进度需要确认。默认从 GitHub 安装并不保证已包含未发布版本的改动。详情和测试方法见[仓库中文使用说明](../../README.zh-CN.md)。
