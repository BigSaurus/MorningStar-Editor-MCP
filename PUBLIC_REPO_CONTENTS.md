# MorningStar Editor MCP Public Repo Contents

This file defines what should and should not be published in the standalone `MorningStar-Editor-MCP` repository.

The goal is to publish the MCP server and its user-facing docs without accidentally publishing reverse-engineering captures, mirrored manuals, generated build artifacts, or local scratch files.

## Include in the public repo

Top-level files:

- `.gitignore`
- `LICENSE`
- `pyproject.toml`
- `requirements.txt`
- `README_MORNINGSTAR_MC8.md`
- `MCP_SHARING_GUIDE.md`
- `PUBLISHING_CHECKLIST.md`
- `MC8_MCP_TOOL_REFERENCE.md`
- `morningstar_mc8_mcp.py`

Tools:

- `tools/generate_mc8_mcp_tool_reference.py`

## Exclude from the public repo

Do not publish these without a deliberate separate decision:

- `captures/`
- `reference/`
- `build/`
- `.wheeltest/`
- `__pycache__/`
- `*.egg-info/`
- `.polyform-noncommercial.txt`

Keep these out unless you decide they are part of the public package story:

- `MC8_MCP_AGENT_HANDOFF.md`
- `MC8_PRO_CONTEXT.md`
- `WEB_EDITOR_BACKUP_SCHEMA_NOTES.md`
- `AXE_FX_LAYOUT_TEMPLATE.md`
- `axefx_factory_layout.json`
- most of `tools/` other than `generate_mc8_mcp_tool_reference.py`

Reasoning:

- `captures/` contains reverse-engineering outputs and raw artifacts that are not needed for end users.
- `reference/` appears to contain mirrored manual content and should not be published by default.
- build and cache directories are local/generated artifacts.
- internal handoff/context notes are useful for development but not necessary for installation or use.

## Minimum publishable repo

If you want the smallest safe public repo, publish exactly this set:

```text
.gitignore
LICENSE
pyproject.toml
requirements.txt
README_MORNINGSTAR_MC8.md
MCP_SHARING_GUIDE.md
PUBLISHING_CHECKLIST.md
MC8_MCP_TOOL_REFERENCE.md
morningstar_mc8_mcp.py
tools/generate_mc8_mcp_tool_reference.py
```

## Export process

Use:

```text
powershell -ExecutionPolicy Bypass -File tools/export_public_repo.ps1 -DestinationPath <new-folder>
```

That script copies only the allowlisted files into a clean destination folder so you can initialize a new standalone repository without carrying over private or research-only material.