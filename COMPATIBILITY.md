# Host compatibility and installation

**Claude, Codex, and official DeepSeek Harness (DSH) can use this reader.** Its runtime
is a local Python script with no model API dependency. The host's skill/plugin loader
determines how to install and invoke it.

| Host | Supported route | Requirement |
| --- | --- | --- |
| Claude Code / Cowork | Claude-compatible marketplace and plugin | Host can execute Python and access your files. |
| Codex desktop / CLI | Compatible plugin marketplace, or standalone Agent Skill | Python and file/shell permissions. |
| Codex IDE extension | Standalone Agent Skill | Python and file/shell permissions; the plugin route is for desktop/CLI. |
| DeepSeek Harness (DSH) | Standalone filesystem skill | DSH skill loader, Python, and file/shell permissions. |
| Terminal without an agent | Direct Python invocation | Python 3; no agent account needed. |

These are the source files shared by all routes:

```text
plugins/novel-txt-reader/skills/novel-txt-reader/
  SKILL.md
  scripts/build_reader.py
  scripts/reader_template.html
  examples/sample.txt
  tests/
```

Copy the **whole skill folder**, including the HTML template. Copying only `SKILL.md`,
or putting the whole repository inside a skill discovery root, is not the right layout.
The converter needs no third-party Python packages, Node, network service, or credentials.
Your agent host has its own authentication requirements. Once generated, the reader
needs only a browser; keep its output folder together.

Version **0.1.2 is unreleased**. Commands that install from GitHub use the selected remote
revision, not unpushed local changes. To try an unreleased checkout, use its local
marketplace path or copy the skill directory from that checkout.

## Claude Code / Cowork

In Claude Code:

```text
/plugin marketplace add mothanaprime/novel-txt-reader
/plugin install novel-txt-reader@novel-txt-reader
```

If a details page opens, choose the install scope and complete installation. For a local
checkout, pass its absolute repository path to `/plugin marketplace add` instead.
In Cowork, use the plugin management UI to add the repository URL and install/enable
`novel-txt-reader`; menu labels vary by client version.

The existing `.claude-plugin/marketplace.json` and plugin manifest remain the Claude
packaging. No conversion code is specific to Claude.

## Codex

### Compatible plugin route (desktop / CLI)

OpenAI's plugin documentation accepts Claude-compatible manifests and the repository
`.claude-plugin/marketplace.json` discovery path. On a CLI that provides `codex plugin`:

```bash
codex plugin marketplace add mothanaprime/novel-txt-reader
codex plugin add novel-txt-reader@novel-txt-reader
```

For a local checkout, replace `mothanaprime/novel-txt-reader` in the first command with
its absolute repository path. Open a new chat after installation and explicitly ask
to use `novel-txt-reader`. Desktop users can also use the plugin management UI.
If an older client lacks these commands, use the standalone skill route below.
This repository is a user-added marketplace; being public on GitHub does not mean it
is listed in OpenAI's public plugin directory.

### Standalone skill route (also shared with DSH)

Codex discovers user skills under `~/.agents/skills`. DSH also searches that location
by default, so one installation can serve both. Run **one** of these examples from the
root of a source checkout. They stop if a same-named destination already exists; review
that existing installation before replacing it.

PowerShell:

```powershell
$skillSource = (Resolve-Path 'plugins/novel-txt-reader/skills/novel-txt-reader').Path
$skillRoot = Join-Path $HOME '.agents/skills'
$skillTarget = Join-Path $skillRoot 'novel-txt-reader'
if (Test-Path -LiteralPath $skillTarget) { throw "Skill already exists: $skillTarget" }
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $skillTarget -Recurse
```

Bash (macOS/Linux):

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

For project-only use, replace the destination root with
`<project-root>/.agents/skills`, then start the host in that project. Codex searches
`.agents/skills` from the working directory up to the repository root. DSH uses the
nearest ancestor containing `.git` as its project root, or the working directory if
there is no Git root. Put the shared project skill at that root for both to find it.

In Codex CLI/IDE, use `/skills` or `$novel-txt-reader`; in desktop, use the skill picker
or name it explicitly in the prompt. Restart the client if the skill does not appear.
Choose either the plugin or standalone installation for a host to avoid duplicate entries.

## DeepSeek Harness (DSH)

This refers specifically to the official
[deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) project
and its `@deepseek-ai/dsh` CLI, not every agent that happens to call a DeepSeek model.

DSH's default filesystem skill loader accepts:

- Shared user root: `~/.agents/skills/novel-txt-reader/SKILL.md`.
- DSH-only user root: `~/.dsh/skills/novel-txt-reader/SKILL.md`.
- Project root: `<project-root>/.agents/skills/novel-txt-reader/SKILL.md` or
  `<project-root>/.dsh/skills/novel-txt-reader/SKILL.md`.

`DSH_HOME` and `DSH_AGENTS_HOME` can change its user roots. The default loader scans one
level of named skills and requires YAML `name` and `description`, both already present
in this skill. It does **not** install the Claude plugin manifest. Use the shared-copy
instructions above, or substitute the DSH-only root.

Start DSH in the intended project and ask, for example:

> 用 novel-txt-reader 把 `C:\Books\book.txt` 生成到 `C:\Books\reader`，完成后核对目录和首章文字。

DSH returns `resourceBase` when it loads the skill. The agent should resolve
`scripts/build_reader.py` against that directory, then run it with an available Python
executable. A customized DSH configuration must keep skill discovery/loading and a
shell tool enabled. Windows DSH includes a PowerShell tool, but this skill does not
bundle Python. Model selection alone does not provide filesystem or command execution.

## Direct script and troubleshooting

From the source repository root, on Windows:

```powershell
python plugins/novel-txt-reader/skills/novel-txt-reader/scripts/build_reader.py plugins/novel-txt-reader/skills/novel-txt-reader/examples/sample.txt sample-reader
```

On macOS/Linux, use `python3`. If Windows uses the Python launcher, use `py -3`.
From another working directory, pass absolute paths to the script, input, and output.
Open `sample-reader/开始阅读.html` in Chrome or Edge after conversion.

| Symptom | Check |
| --- | --- |
| Skill missing | Check the root and one-level folder layout; reopen the host. DSH project root can differ from the shell's current subdirectory. |
| Script/template missing | Copy the entire skill folder; resolve scripts relative to `SKILL.md` or `resourceBase`. |
| Python unavailable | Select an installed Python 3 executable in the same environment where the host runs commands. |
| File access denied | Give the host access to the TXT and a writable output folder; local paths must exist inside a remote/sandboxed host too. |
| Encoding ambiguous | Inspect the source and pass a known encoding, e.g. `--encoding big5` or `--encoding gb18030`. Do not guess that a successful decode is correct. |

## Verification scope

Checked on **2026-10-09** against the local 0.1.2 source:

| Check | Evidence / limit |
| --- | --- |
| Claude Code 2.1.197 | `claude plugin validate .` and validation of `plugins/novel-txt-reader` passed. Format validation is not a Cowork/Claude model invocation. |
| Codex CLI 0.142.5 | Official docs confirm compatible manifests and standalone roots; local CLI help confirms marketplace/add commands. No fresh 0.1.2 plugin installation or model-driven conversion was performed. |
| DSH 0.1.1-rc.2 | The installed native `FileSystemSkillProvider` discovered and loaded this skill using an isolated custom root, with no warnings; `resourceBase` resolved the Python script, HTML template, and sample. This tested loading, not a DSH model-driven conversion. |
| Converter and reader | Python regression suite and real Chromium browser checks cover generated output and reading behavior; see the [README test instructions](README.md#development--tests). These are independent of host prompting. |

The DSH probe disabled default roots and file watching and did not install anything or
call a model. Client behavior can change between releases; the standalone skill and
direct script remain available when a plugin management UI differs.

## Official references

- [Claude plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
  and [plugin installation](https://code.claude.com/docs/en/plugins/install).
- [OpenAI: build skills](https://learn.chatgpt.com/docs/build-skills)
  and [plugin manifests and marketplaces](https://developers.openai.com/plugins/build/plugins).
- [DSH filesystem skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md),
  [skill loading](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/tool-skill/README.md),
  [resourceBase](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md#L233),
  and [PowerShell tool](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/shell/tool-pwsh/README.md).
