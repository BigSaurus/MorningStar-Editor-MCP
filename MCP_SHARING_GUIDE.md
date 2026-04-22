# MorningStar Editor MCP Sharing Guide

This guide covers the simplest ways to distribute the Morningstar MC8 Pro MCP server so other people can install it and wire it into their MCP client with minimal setup.

## Recommended packaging model

Treat the MC8 server as a normal Python package that exposes one console command:

- package name: `morningstar-mc8-mcp`
- console command: `morningstar-mc8-mcp`
- entrypoint: `morningstar_mc8_mcp:main`

That lets MCP clients launch the server as a plain stdio command without custom wrapper scripts.

## Distribution options

There are two good ways to publish this package.

### Option 1: Standalone repository

This is the cleanest share path.

Put the contents of the `MC8 Pro` folder in their own Git repository root, then users can install with:

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

Why this is best:

- shortest install command
- easiest README and release tagging story
- no need to explain subdirectory installs
- easier to publish later to PyPI if you want

Minimum files to carry into the standalone repo:

- `morningstar_mc8_mcp.py`
- `pyproject.toml`
- `requirements.txt`
- `README.md`
- `MC8_MCP_TOOL_REFERENCE.md`
- `MCP_SHARING_GUIDE.md`
- `tools/generate_mc8_mcp_tool_reference.py`

### Option 2: Keep it in a monorepo subdirectory

If you want to keep sharing from the current parent repo, install from the subdirectory:

```text
pipx install git+https://github.com/BigSaurus/<repo>.git#subdirectory=MC8%20Pro
```

This works fine, but it is slightly harder for other people to discover and remember.

Use this when:

- the MC8 project still depends on nearby repo context
- you do not want a separate public repository yet
- you want to keep cross-project history together for now

## Local verification before sharing

From the `MC8 Pro` directory:

```text
python -m py_compile morningstar_mc8_mcp.py tools/generate_mc8_mcp_tool_reference.py
python tools/generate_mc8_mcp_tool_reference.py --check
python -m pip wheel . --no-deps
```

That confirms:

- the MCP server still imports
- the checked-in tool reference is in sync
- the package metadata can build a wheel

## Install commands for users

### From a local checkout

```text
pipx install .
```

### From a standalone Git repository

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

### From a monorepo subdirectory

```text
pipx install git+https://github.com/BigSaurus/<repo>.git#subdirectory=MC8%20Pro
```

## MCP client config examples

These examples assume the package is already installed and that `morningstar-mc8-mcp` is available on `PATH`.

Before finalizing the config, use the MCP tool `list_midi_ports` once to discover the correct `MORNINGSTAR_MC8_MIDI_OUT` and `MORNINGSTAR_MC8_MIDI_IN` values for the target machine.

### VS Code example

Example MCP server entry for a VS Code MCP configuration file:

```json
{
  "servers": {
    "morningstar-mc8": {
      "type": "stdio",
      "command": "morningstar-mc8-mcp",
      "args": [],
      "env": {
        "MORNINGSTAR_MC8_MIDI_OUT": "Morningstar MC8 Pro 3",
        "MORNINGSTAR_MC8_MIDI_IN": "Morningstar MC8 Pro 2"
      }
    }
  }
}
```

If VS Code is launched from an environment that does not inherit the `pipx` script path, point `command` at the full executable path instead.

### Claude Desktop example

Example `claude_desktop_config.json` entry:

```json
{
  "mcpServers": {
    "morningstar-mc8": {
      "command": "morningstar-mc8-mcp",
      "args": [],
      "env": {
        "MORNINGSTAR_MC8_MIDI_OUT": "Morningstar MC8 Pro 3",
        "MORNINGSTAR_MC8_MIDI_IN": "Morningstar MC8 Pro 2"
      }
    }
  }
}
```

On Windows, if Claude Desktop cannot find the `pipx` shim, replace `command` with the full path to the installed executable.

## Recommended path for this project

For the current codebase, the best near-term share path is:

1. keep the package installable from the `MC8 Pro` subdirectory right now
2. document the subdirectory install command clearly
3. move it to the `MorningStar-Editor-MCP` standalone repository once you want cleaner public sharing and tagged releases

That keeps your current workspace structure intact while still giving other people a one-command install path.