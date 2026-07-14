# MorningStar Editor MCP

Python MCP server for controlling a Morningstar MC8 Pro foot controller over USB MIDI SysEx.

It exposes the MC8 Pro as a regular stdio MCP server: live probe tools, bank navigation, preset-label
editing, documented PC and CC message programming, offline Morningstar-style backup JSON helpers, and —
via a reverse-engineered editor protocol — **persistent bank writes that commit to the controller's flash
and survive a power-cycle**.

License: PolyForm Noncommercial 1.0.0 — source-available for noncommercial use (see [License](#license)).

## Quick start

Install:

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

For local development from a checkout:

```text
pip install -e .
```

Point your MCP client at the console command `morningstar-mc8-mcp` and set the MIDI ports for your machine:

```text
MORNINGSTAR_MC8_MIDI_OUT=Morningstar MC8 Pro 3
MORNINGSTAR_MC8_MIDI_IN=Morningstar MC8 Pro 2
```

If you do not know the port names yet, launch the server through your MCP client and call `list_midi_ports`,
then fill in the two variables. Requires Python 3.10+; dependencies (`mido`, `python-rtmidi`, `mcp`,
`python-dotenv`) install automatically. Use a wired USB connection to the MC8 Pro `USB Device` port.

### MCP client config

Generic MCP server entry:

```json
{
  "mcpServers": {
    "morningstar-mc8": {
      "command": "morningstar-mc8-mcp",
      "env": {
        "MORNINGSTAR_MC8_MIDI_OUT": "Morningstar MC8 Pro 3",
        "MORNINGSTAR_MC8_MIDI_IN": "Morningstar MC8 Pro 2"
      }
    }
  }
}
```

Client-specific examples (VS Code, Claude Desktop) are in [`MCP_SHARING_GUIDE.md`](MCP_SHARING_GUIDE.md).
If your client cannot find the `pipx` shim, set `command` to the full path of the installed executable.

## What this server can do

- inspect the current bank and preset labels; read toggle states and controller info
- navigate bank up, bank down, and toggle page
- rename the current bank and preset labels (working memory)
- write documented Program Change and Control Change preset messages
- write `CC0 + optional CC32 + PC` into adjacent message slots
- program the selected bank from JSON
- **persistently flash a bank so it survives a power-cycle** — use [`safe_flash_bank`](#persistent-bank-writes-flash)
  (guarded, recommended) or the low-level `upload_current_bank_from_json`
- generate and inspect Morningstar-style backup JSON offline
- generate an editor-importable, hash-valid all-banks backup file for restore through the official editor

It is not a full replacement for the Morningstar editor — see [Scope and limitations](#scope-and-limitations).

## Persistent bank writes (flash)

The documented `0x70` SysEx write functions only edit the controller's **working memory**: `save=True`
(opcode `0x7F`) keeps an edit across bank changes but it is **lost on power-cycle**. Committing to flash
uses a separate, reverse-engineered **group-7 upload protocol** (the same one the official editor runs over
USB MIDI), which was recovered from a USB capture of a real editor restore.

A critical property of that protocol: **it writes to the bank the controller is currently navigated to.**
The `bank_number` argument is only embedded as chunk metadata — it does not select the target bank. So
uploading while parked on the wrong bank silently corrupts that bank. Use the guarded tool below.

### `safe_flash_bank` (recommended)

The safe, position-verified way to persist one bank. It:

1. auto-resolves the primary (cable 0) Morningstar port pair, tolerating USB re-enumeration,
2. navigates to the target bank by walking bank-up to a **known-unique** landmark bank name, then stepping,
3. **guards the write**: it probes the current bank name and requires it to equal `expect_current_bank_name`
   before sending anything — a mismatch raises `BankPositionError` and **nothing is written**,
4. flashes the bank via the group-7 protocol and sends the completion signal.

`dry_run=True` rehearses the navigation and guard without writing. Because a real write leaves the
controller in editor-session mode, **flash one bank per power-cycle**: power-cycle the MC8 before flashing
another bank or verifying with probes.

### `upload_current_bank_from_json` (low-level)

Runs the connect handshake, streams the bank/preset chunks with the device's request/ACK flow, and commits
to flash. It writes to the **currently navigated bank** (see the warning above), so prefer `safe_flash_bank`.
If you call it directly, pass `expect_current_bank_name` to enable the same pre-write guard.

### `build_editor_native_restore_file` (offline)

Generates an editor-native, hash-valid all-banks backup file from a layout, so you can restore through the
official Morningstar editor without any code touching the device.

### Caveats

- After a flash upload the controller stays in editor-session mode (real-time `0x70` probes are disabled)
  until you power-cycle it. The flash write itself is already committed.
- The `0x70` name/message setters remain working-memory only. Use a flash upload (or an editor restore)
  when you need changes to persist.

## Tool reference

The complete tool surface — parameters, safety level, transport behavior, and verification status — is in
[`MC8_MCP_TOOL_REFERENCE.md`](MC8_MCP_TOOL_REFERENCE.md). It is generated from `morningstar_mc8_mcp.py`, so
the documented list stays aligned with the actual server. Regenerate it with:

```text
python tools/generate_mc8_mcp_tool_reference.py
```

CI enforces that the checked-in file matches the source with `python tools/generate_mc8_mcp_tool_reference.py --check`.

## Scope and limitations

Good for: current-bank inspection, bank/preset naming updates, preset label updates, PC / CC /
bank-select-plus-PC programming, controller navigation and page toggling, JSON-driven programming of the
selected bank, **persistent flash writes of a bank**, and generation/inspection of draft backup JSON.

Not yet implemented as live tools: full editor message-family coverage beyond PC/CC, full-bank live
readback, all-banks live restore to hardware, controller-global settings writes, and profile
switching/editing. The reverse-engineering background, SysEx framing reference, and roadmap are in
[`DESIGN.md`](DESIGN.md).

## Packaging and sharing

This is a normal Python package with a console entrypoint:

- installable package metadata in `pyproject.toml`
- console command `morningstar-mc8-mcp`
- runtime entrypoint `morningstar_mc8_mcp:main`

That keeps integration simple: an MCP client only needs to launch one command on `PATH`. For distribution
layouts and more client config examples, see [`MCP_SHARING_GUIDE.md`](MCP_SHARING_GUIDE.md).

Maintainer notes for cutting a release are in [`PUBLISHING_CHECKLIST.md`](PUBLISHING_CHECKLIST.md).

## License

Released under PolyForm Noncommercial 1.0.0 (see `LICENSE`). This is a source-available noncommercial
license, not an open-source license: you may download, use, study, and share it for noncommercial purposes,
but not for commercial use.

One consequence worth knowing: anyone who receives a version under this license keeps the rights granted for
that version. Future versions may use different terms, but past releases do not become retroactively more
restrictive.
