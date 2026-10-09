# novel-txt-reader 中文使用说明

[English](README.md) | 简体中文

把一本 `.txt` 小说转换成**按章节加载、支持书签的离线 HTML 阅读器**。适合数千章的
中文网文，也可以处理其他 TXT 书籍。生成后双击「开始阅读.html」即可阅读，不需要服务器。

它包含一份通用 skill 和 Python 脚本，同时提供 Claude 兼容插件包装。
**Claude、Codex、DeepSeek 官方 Harness（DSH）共用同一套转换代码**。

本文对应 **0.1.2，尚未正式发布**。从 GitHub 默认安装得到的是所选远端版本；修复分支
合并前，不能把这里的新功能说明当作 `main` 已经包含这些改动。

## 选择使用方式

| 你使用的工具 | 安装方式 |
| --- | --- |
| Claude Code / Cowork | 添加本仓库为插件市场，再安装 `novel-txt-reader`。 |
| Codex 桌面版 / CLI | 使用兼容插件市场，或安装独立 skill。 |
| Codex IDE 扩展 | 安装独立 skill。 |
| DeepSeek Harness（DSH） | 将完整 skill 目录放入 `.agents/skills` 或 `.dsh/skills`。 |
| 不使用 AI 工具 | 直接运行下面的 Python 命令。 |

完整安装步骤、不同工具的目录规则和官方依据见[中文兼容性指南](COMPATIBILITY.zh-CN.md)。
Codex 与 DSH 可共用 `~/.agents/skills/novel-txt-reader`。
**复制时要保留整个技能目录，不能只复制 `SKILL.md`**；脚本还需要旁边的 HTML 模板。

生成需要 **Python 3**，不需要额外 Python 包。使用 agent 时，它还需要读取 TXT、
写入输出目录和运行命令的权限。转换器本身不需要账号或 API 密钥；AI 工具可能需要自己的登录。
**阅读已生成的书只需要浏览器**，不需要 Python 或 Node。

## 快速开始

### 让 AI 工具生成

安装并启用技能后，提供清楚的输入、输出路径，例如：

> 用 novel-txt-reader 把 `C:\Books\我的小说.txt` 转成离线阅读器，输出到
> `C:\Books\我的小说-阅读器`，完成后检查目录和首章文字。

这些路径必须在 AI 工具实际运行的环境中可访问；远程或沙箱环境不一定能直接访问本机文件。
如果工具找不到 Python 或没有文件权限，应先解决对应问题。

### 自己运行脚本

打开终端，进入本项目的源码根目录（能看到 `plugins` 文件夹的位置）。
Windows PowerShell：

```powershell
python "plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py" "C:\Books\我的小说.txt" "C:\Books\我的小说-阅读器"
```

如果本机使用 Python 启动器，把 `python` 换成 `py -3`。macOS / Linux 使用 `python3`：

```bash
python3 "plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py" \
  "/path/to/book.txt" "/path/to/reader"
```

在其他目录运行时，请把脚本、TXT 和输出目录都写成绝对路径。路径中有空格时保留引号。
省略输出目录时，会在 TXT 旁边创建以书名命名的文件夹。

也可以先用仓库自带的原创短样例试用，在源码根目录运行：

```powershell
python "plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py" "plugins/novel-txt-reader/skills/novel-txt-reader/examples/sample.txt" "sample-reader"
```

完成后，用 Chrome 或 Edge 打开输出目录里的 **「开始阅读.html」**。
先核对目录和前几章的文字，确认章节切分和编码符合原文。

### 提示编码不确定时

支持 UTF-8、带 BOM 的 UTF-16，以及 GBK / GB18030 / Big5 等编码。遇到无法可靠区分的
旧编码，脚本会停止，要求明确指定编码，不会用替换字符悄悄掩盖损坏字节。

确认原文件是 Big5 后，可以这样运行：

```powershell
python "plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py" "C:\Books\我的小说.txt" "C:\Books\我的小说-阅读器" --encoding big5
```

GB18030 文件可使用 `--encoding gb18030`。不要只因为命令执行成功就认定编码正确，
仍需检查生成文字。[常见问题](COMPATIBILITY.zh-CN.md)中还有路径、权限和技能发现的排查方法。

## 阅读器怎么用

| 功能 | 操作 |
| --- | --- |
| 目录与搜索 | 打开顶部「目录」，按卷浏览、搜索章节名或跳到指定章节。 |
| 上一章 / 下一章 | 使用页面翻页按钮，或键盘 `←` / `→`。 |
| 自动续读 | 阅读位置会自动保存；用同一浏览器重新打开，可恢复章节和滚动比例。 |
| 手动书签 | 点击右下角书签按钮或打开「书签」面板；也可按 `B` 添加。支持跳转和删除。 |
| 外观 | 顶部「Aa」可调整日间 / 护眼 / 夜间主题、字体、字号、行距和宽度。 |
| 导出 / 导入进度 | 在「书签」面板导出 JSON 备份；换设备、移动文件夹或清理浏览器前先导出。 |

进度保存在**浏览器本地存储**，没有账号同步服务；换浏览器不会自动带上进度。
恢复位置依据滚动比例，字号、窗口或设备改变后，屏幕上具体显示的句子可能有所偏移。
章节加载失败时，会保留之前的正文和位置。

导入前会完整校验备份。损坏的备份或其他书的备份会被拒绝，已有进度不受影响。

## 支持的章节与输出文件

- 根据主要章节标记识别 `第X章`、`第X回`、`第X节` 或 `Chapter N`，减少副标题导致的误拆。
- 按卷 / 部 / 集分组，保留楔子、序章、番外、外传等特殊部分。
- 正文中的网址、普通句子和分隔行会保留；可疑标题按正文处理。
- 没有识别到章节时，按大小切成「第N部分」。
- 每次只加载一章，适合长篇书籍；可以直接从本地 `file://` 打开。

```text
输出目录/
  开始阅读.html            # 用浏览器打开
  使用说明.txt              # 随书附带的中文说明
  .novel-txt-reader.json    # 生成文件归属清单，保留在原处
  data/
    catalog.js             # 书籍标识和目录
    ch_0000.js ...          # 每章一个文件
```

请保留完整目录结构。移动或复制书籍时，整个文件夹一起移动，不要只带走 HTML。
移动前先导出进度，因为浏览器对本地文件的存储可能随路径变化。

## 更新阅读器与保留旧进度

先导出进度、备份旧阅读器，再用新脚本对同一 TXT 和输出目录重新生成。
脚本会先准备待更新文件，再替换自己管理的内容，保留无关文件，并在普通写入或替换错误时回滚。
这不等同于断电或磁盘故障时整个目录的原子更新，外部备份仍应保留。

进度按正文内容生成的书籍 ID 隔离。同样的文本仅移动位置或更换编码时保持 ID；
修改正文会得到新 ID。旧版 0.1.1 进度没有书籍 ID，需要用户确认后才迁移，原始记录会保留。
修正章节识别后，部分旧章节引用可能不再匹配，此类进度会被拒绝，不会猜测跳到哪一章。

## 开发与测试

在源码根目录运行 Python 回归，不需要额外包：

```powershell
python -m unittest discover -s plugins/novel-txt-reader/skills/novel-txt-reader/tests -p "test_*.py" -v
```

浏览器回归使用固定版本 Playwright 和真实 Chromium；测试内容均为合成文本。
从源码根目录运行：

```bash
npm ci
npx playwright install chromium
npm test
```

可分别运行 `npm run test:python` 和 `npm run test:browser`。
环境变量 `PYTHON` 可选择已有 Python 可执行文件，`CHROME_EXECUTABLE_PATH` 可选择已安装的
Chrome，避免额外下载 Chromium。Node / Playwright 仅用于开发测试，不是阅读或转换必需品。

CI 同时在 Linux、Windows 执行。Windows 本机若缺少创建符号链接权限，相关测试会跳过；
必须检查结果是 `ok` 还是 `skipped`，不能只看整个命令是否返回成功。
2026-10-09 的[修复版 CI](https://github.com/mothanaprime/novel-txt-reader/actions/runs/37919706118)
已在两个平台各通过 24 项 Python 和 14 组浏览器测试，两项符号链接测试均实际执行，零跳过。

## 分支、版本和发布

项目共用一个 `main` 主分支。Claude、Codex、DSH 是不同安装入口，不是三个需要分别合并的版本。

1. 在短期修复或功能分支上修改，通过 PR 审查和 CI 后合并到 `main`。
2. 准备正式发布时，同步插件清单版本号和更新记录，再在确定的提交上创建如 `v0.1.2` 的标签及 Release。
3. 旧版本保留在 Git 历史、标签和 Release 中，不需要长期维护 `0.1.1`、`0.1.2` 两套主分支。

**合并到 `main` 与发布 Release 是两步操作**。`main` 代表已合入的最新代码；带版本的标签固定
一次发布的源码。中英文文档也放在同一分支，功能变动时同步更新。

## 许可

[MIT](LICENSE)。本仓库只包含工具与一小段原创示例，不应把有版权的小说正文提交到公开仓库。
变更详情见 [CHANGELOG.md](CHANGELOG.md)。
