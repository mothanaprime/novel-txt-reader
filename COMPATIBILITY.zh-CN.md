# 宿主兼容性与安装说明

[English](COMPATIBILITY.md) | 简体中文 | [中文使用说明](README.zh-CN.md)

**Claude、Codex 和官方 DeepSeek Harness（DSH）都可以使用这个阅读器。** 转换工作由本地 Python 脚本完成，不依赖任何模型 API。具体安装和调用方式，取决于宿主的技能或插件加载机制。

| 宿主 | 支持的使用方式 | 前提条件 |
| --- | --- | --- |
| Claude Code / Cowork | Claude 兼容的插件市场与插件 | 宿主能够执行 Python，并访问你的文件。 |
| Codex 桌面版 / CLI | 兼容的插件市场，或独立 Agent Skill | Python，以及文件访问和命令执行权限。 |
| Codex IDE 扩展 | 独立 Agent Skill | Python，以及文件访问和命令执行权限；插件方式适用于桌面版和 CLI。 |
| DeepSeek Harness（DSH） | 独立的文件系统技能 | DSH 技能加载器、Python，以及文件访问和命令执行权限。 |
| 不使用代理的终端 | 直接运行 Python 脚本 | Python 3；无需代理账号。 |

各种方式使用的是同一组源文件：

```text
plugins/novel-txt-reader/skills/novel-txt-reader/
  SKILL.md
  scripts/build_reader.py
  scripts/reader_template.html
  examples/sample.txt
  tests/
```

请复制**整个技能文件夹**，包括 HTML 模板。只复制 `SKILL.md`，或把整个仓库放进技能搜索目录，都不符合所需的目录结构。转换器不需要第三方 Python 包、Node、网络服务或凭据；代理宿主可能有自己的登录要求。生成后只需浏览器即可阅读，请保持输出文件夹完整。

本文对应 **0.1.2**。固定版本源码可从 [v0.1.2 Release](https://github.com/mothanaprime/novel-txt-reader/releases/tag/v0.1.2) 获取。从 GitHub 安装时，获取的是所选远端版本，`main` 可能在发布后继续更新。要使用特定的本地源码版本，请提供它的本地插件市场路径，或复制其中的完整技能文件夹。

## Claude Code / Cowork

在 Claude Code 中执行：

```text
/plugin marketplace add mothanaprime/novel-txt-reader
/plugin install novel-txt-reader@novel-txt-reader
```

如果打开了详情页，请选择安装范围并完成安装。如果使用本地检出目录，将第一条命令中的仓库名称替换为仓库的绝对路径即可。

在 Cowork 中，通过插件管理界面添加仓库 URL，再安装并启用 `novel-txt-reader`；不同客户端版本的菜单名称可能不同。

现有 `.claude-plugin/marketplace.json` 和插件清单仍用于 Claude 插件打包。转换代码本身不依赖 Claude。

## Codex

### 兼容插件方式（桌面版 / CLI）

OpenAI 的插件文档支持 Claude 兼容的清单，以及仓库中的 `.claude-plugin/marketplace.json` 搜索路径。如果 CLI 提供 `codex plugin` 命令，可执行：

```bash
codex plugin marketplace add mothanaprime/novel-txt-reader
codex plugin add novel-txt-reader@novel-txt-reader
```

如果使用本地检出目录，将第一条命令中的 `mothanaprime/novel-txt-reader` 替换为仓库绝对路径。安装后新建聊天，并明确要求使用 `novel-txt-reader`。桌面版也可以使用插件管理界面。

如果旧版客户端没有这些命令，可使用下方的独立技能方式。本仓库属于用户自行添加的插件市场；在 GitHub 公开，并不代表已收录到 OpenAI 的公共插件目录。

### 独立技能方式（也可与 DSH 共用）

Codex 会在 `~/.agents/skills` 下发现用户技能，DSH 默认也搜索这个位置，因此安装一份即可供两者使用。从源码仓库根目录运行以下**一组**命令。如果目标位置已存在同名技能，示例会停止复制；请先检查原有安装，再决定是否替换。

PowerShell：

```powershell
$skillSource = (Resolve-Path 'plugins/novel-txt-reader/skills/novel-txt-reader').Path
$skillRoot = Join-Path $HOME '.agents/skills'
$skillTarget = Join-Path $skillRoot 'novel-txt-reader'
if (Test-Path -LiteralPath $skillTarget) { throw "Skill already exists: $skillTarget" }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $skillTarget -Recurse
```

Bash（macOS/Linux）：

```bash
skill_source="plugins/novel-txt-reader/skills/novel-txt-reader"
skill_root="$HOME/.agents/skills"
skill_target="$skill_root/novel-txt-reader"
if [ -e "$skill_target" ] || [ -L "$skill_target" ]; then
  printf '%s\n' "Skill already exists: $skill_target"
else
  mkdir -p "$skill_root" && cp -R "$skill_source" "$skill_target"
fi
```

如果只想在某个项目中使用，将目标根目录改为 `<project-root>/.agents/skills`，然后在该项目中启动宿主。Codex 会从当前工作目录向上搜索 `.agents/skills`，直到仓库根目录。DSH 则将最近的、包含 `.git` 的祖先目录作为项目根目录；如果找不到 Git 根目录，就使用当前工作目录。将共用技能放在项目根目录下，可让两者都找到它。

在 Codex CLI / IDE 中，可使用 `/skills` 或 `$novel-txt-reader`；在桌面版中，可通过技能选择器选择，或在提示词中明确写出技能名称。如果没有显示，请重启客户端。对于同一宿主，插件方式和独立技能方式任选其一，避免出现重复条目。

## DeepSeek Harness（DSH）

这里特指官方 [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 项目及其 `@deepseek-ai/dsh` CLI，并非所有调用 DeepSeek 模型的代理程序。

DSH 默认的文件系统技能加载器支持以下位置：

- 共用用户目录：`~/.agents/skills/novel-txt-reader/SKILL.md`。
- DSH 专用用户目录：`~/.dsh/skills/novel-txt-reader/SKILL.md`。
- 项目目录：`<project-root>/.agents/skills/novel-txt-reader/SKILL.md` 或 `<project-root>/.dsh/skills/novel-txt-reader/SKILL.md`。

`DSH_HOME` 和 `DSH_AGENTS_HOME` 可以更改用户目录。默认加载器扫描一层按技能命名的目录，并要求 YAML 中包含 `name` 和 `description`；本技能已经具备这些字段。它**不会通过 Claude 插件清单安装插件**。请使用上方的共用目录复制方法，或将目标改为 DSH 专用目录。

在目标项目中启动 DSH，然后提出请求，例如：

> 用 novel-txt-reader 把 `C:\Books\book.txt` 生成到 `C:\Books\reader`，完成后核对目录和首章文字。

DSH 加载技能时会返回 `resourceBase`。代理应以该目录为基准，定位 `scripts/build_reader.py`，再使用可用的 Python 可执行文件运行它。自定义 DSH 配置需要保留技能发现、技能加载和 shell 工具。Windows 版 DSH 提供 PowerShell 工具，但本技能不附带 Python。仅选择某个模型，并不会自动提供文件访问或命令执行能力。

## 直接运行脚本与故障排查

在 Windows 上，从源码仓库根目录运行：

```powershell
python plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py plugins/novel-txt-reader/skills/novel-txt-reader/examples/sample.txt sample-reader
```

macOS/Linux 使用 `python3`。如果 Windows 使用 Python 启动器，可改为 `py -3`。从其他工作目录运行时，请为脚本、输入文件和输出目录提供绝对路径。转换后用 Chrome 或 Edge 打开 `sample-reader/开始阅读.html`。

| 问题 | 排查方法 |
| --- | --- |
| 找不到技能 | 检查技能根目录和一层文件夹结构，重新打开宿主。DSH 的项目根目录可能与 shell 当前所在的子目录不同。 |
| 找不到脚本或模板 | 复制完整技能文件夹，并相对于 `SKILL.md` 所在目录或 `resourceBase` 定位脚本。 |
| 找不到 Python | 选择已安装的 Python 3，并确认它在宿主执行命令的环境中可用。 |
| 文件访问被拒绝 | 允许宿主读取 TXT，并选择可写的输出目录。使用远程或沙箱宿主时，这些路径也必须在该环境内存在。 |
| 编码存在歧义 | 检查源文件后明确指定编码，例如 `--encoding big5` 或 `--encoding gb18030`。能够解码不代表解码结果正确。 |

## 验证范围

以下检查于 **2026-10-09** 针对本地 0.1.2 源码完成：

| 检查项目 | 证据与范围 |
| --- | --- |
| Claude Code 2.1.197 | `claude plugin validate .` 及对 `plugins/novel-txt-reader` 的校验均通过。这是格式校验，不是 Cowork / Claude 模型调用测试。 |
| Codex CLI 0.142.5 | 官方文档确认支持兼容清单和独立技能目录；本地 CLI 帮助确认提供 marketplace / add 命令。没有重新安装 0.1.2 插件，也没有进行由模型驱动的转换测试。 |
| DSH 0.1.1-rc.2 | 已安装的原生 `FileSystemSkillProvider` 通过隔离的自定义根目录发现并加载了本技能，无警告；通过 `resourceBase` 成功定位 Python 脚本、HTML 模板和样例。这验证了加载流程，不是由 DSH 模型驱动的转换测试。 |
| 转换器与阅读器 | Python 回归测试及真实 Chromium 浏览器检查覆盖了生成结果和阅读行为，参见 [README 中的测试说明](README.zh-CN.md)。这些测试独立于宿主的提示词调用过程。 |

DSH 探测禁用了默认搜索目录和文件监听，没有安装任何内容，也没有调用模型。客户端行为可能随版本变化；当插件管理界面不同时，仍可使用独立技能或直接运行脚本。

## 官方参考资料

- [Claude 插件市场](https://code.claude.com/docs/en/plugin-marketplaces)和[插件安装](https://code.claude.com/docs/en/plugins/install)。
- [OpenAI：构建技能](https://learn.chatgpt.com/docs/build-skills)和[插件清单与插件市场](https://developers.openai.com/plugins/build/plugins)。
- [DSH 文件系统技能](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)、[技能加载](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md)、[resourceBase](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md#L233)和 [PowerShell 工具](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/shell/tool-pwsh/README.md)。
