# MorningStar Editor MCP Sharing Guide

This guide covers the simplest ways to distribute the Morningstar MC8 Pro MCP server so other people can
install it and wire it into their MCP client with minimal setup.

## Recommended packaging model

Treat the MC8 server as a normal Python package that exposes one console command:

- package name: `morningstar-mc8-mcp`
- console command: `morningstar-mc8-mcp`
- entrypoint: `morningstar_mc8_mcp:main`

That lets MCP clients launch the server as a plain stdio command without custom wrapper scripts.

## Installing

### From the standalone Git repository

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

### From a local checkout

```text
pipx install .
```

or, for development:

```text
pip install -e .
```

## Local verification before sharing

From the repository root:

```text
python -m py_compile morningstar_mc8_mcp.py tools/generate_mc8_mcp_tool_reference.py
python tools/generate_mc8_mcp_tool_reference.py --check
python -m pip wheel . --no-deps
```

That confirms the MCP server still imports, the checked-in tool reference is in sync, and the package
metadata can build a wheel.

## MCP client config examples

These examples assume the package is already installed and that `morningstar-mc8-mcp` is available on
`PATH`. Before finalizing the config, call the MCP tool `list_midi_ports` once to discover the correct
`MORNINGSTAR_MC8_MIDI_OUT` and `MORNINGSTAR_MC8_MIDI_IN` values for the target machine.

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

If VS Code is launched from an environment that does not inherit the `pipx` script path, point `command`
at the full executable path instead.

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

On Windows, if Claude Desktop cannot find the `pipx` shim, replace `command` with the full path to the
installed executable.
