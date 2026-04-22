# MorningStar Editor MCP

Python MCP server for controlling a Morningstar MC8 Pro over USB MIDI SysEx.

GitHub repository name: `MorningStar-Editor-MCP`

Current license: PolyForm Noncommercial 1.0.0. That means people can use, study, and share this project for noncommercial purposes, but not for commercial use.

This project exposes the MC8 Pro as a regular stdio MCP server, with live probe tools, bank navigation, preset-label editing, documented PC and CC message programming, and offline Morningstar-style backup JSON helpers.

## Quick start

Install from the standalone repo root with:

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

For local development:

```text
pip install -e .
```

Then point your MCP client at:

```text
morningstar-mc8-mcp
```

with these environment variables set for the target machine:

```text
MORNINGSTAR_MC8_MIDI_OUT=Morningstar MC8 Pro 3
MORNINGSTAR_MC8_MIDI_IN=Morningstar MC8 Pro 2
```

If the correct MIDI port names are not known yet, connect through your MCP client first and call `list_midi_ports`.

## What this server can do

- inspect the current bank and preset labels
- navigate bank up, bank down, and toggle page
- rename the current bank and preset labels
- write documented Program Change and Control Change preset messages
- write `CC0 + optional CC32 + PC` into adjacent message slots
- program the selected bank from JSON
- generate and inspect Morningstar-style backup JSON locally

## License

This project is currently released under PolyForm Noncommercial 1.0.0. See `LICENSE`.

That is a source-available noncommercial license, not an open-source license.

This fits the current goal:

- people can download and use it for free now
- you keep commercial control
- you can offer paid commercial licensing later if you want

One important consequence: anyone who gets a version under this license keeps the rights granted by this license for that version. Future versions can use different terms, but past releases do not become retroactively more restrictive.

## Integration examples

For concrete config examples, use:

- `MCP_SHARING_GUIDE.md`

That guide includes copy-paste MCP config examples for VS Code and Claude Desktop.

## MCP tool reference

For the complete regular-MCP tool surface, including parameters, safety level, transport behavior, and verification status, use:

- `MC8_MCP_TOOL_REFERENCE.md`

That file is generated from `morningstar_mc8_mcp.py` so the documented tool list stays aligned with the actual server.

Regenerate it with:

```text
python tools/generate_mc8_mcp_tool_reference.py
```

The repository CI also enforces this file with:

```text
python tools/generate_mc8_mcp_tool_reference.py --check
```

If the checked-in reference drifts from the current server source, the MC8 tool-reference workflow fails.

## Packaging and sharing

The easiest way to share this MCP server is as a normal Python package with a console entrypoint.

This project now supports that shape directly:

- installable package metadata lives in `pyproject.toml`
- the console command is `morningstar-mc8-mcp`
- the runtime entrypoint is `morningstar_mc8_mcp:main`

That keeps integration simple for other people because their MCP client only needs to launch one command on `PATH`.

### Recommended share path

If you host this folder as its own Git repository, the simplest install flow for other users is:

```text
pipx install git+https://github.com/BigSaurus/MorningStar-Editor-MCP.git
```

If you keep sharing from a monorepo during transition, the subdirectory install also works:

```text
pipx install git+https://github.com/BigSaurus/<repo>.git#subdirectory=MC8%20Pro
```

For local testing before publishing:

```text
pip install -e .
```

or:

```text
pipx install .
```

### MCP client integration

After installation, point the client at the console script and set the MIDI ports through environment variables.

Generic MCP config shape:

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

If the user has not pinned ports yet, they should first run:

```text
morningstar-mc8-mcp
```

through their MCP client and call `list_midi_ports` from the tool surface, then fill in the two environment variables with the correct device names.

### What to publish

For a simple shareable release, publish these files together:

- `morningstar_mc8_mcp.py`
- `pyproject.toml`
- `requirements.txt`
- `MC8_MCP_TOOL_REFERENCE.md`
- `README_MORNINGSTAR_MC8.md`

That is enough for a Git-based install and for normal MCP client integration without custom wrappers.

For concrete distribution layouts and client config examples, see:

- `MCP_SHARING_GUIDE.md`

## Before publishing publicly

Before making the standalone repo public, do these repo-level checks:

1. Review the included `LICENSE` file and confirm PolyForm Noncommercial 1.0.0 still matches how you want to share the repo.
2. Replace placeholder GitHub URLs in this README and in `MCP_SHARING_GUIDE.md`.
3. Run `python tools/generate_mc8_mcp_tool_reference.py --check`.
4. Run `python -m pip wheel . --no-deps` from the repo root.
5. Test one end-to-end MCP client config using the packaged `morningstar-mc8-mcp` command.

## Recommendation

Use direct USB MIDI plus Morningstar's documented SysEx API as the primary integration path.

This is the right first move because:

- it avoids WebMIDI/browser permission problems
- it avoids UI automation against the web or desktop editor
- it gives us deterministic request/response control over a documented transport
- the workspace already has the required Python MIDI stack: `mido` and `python-rtmidi`

Do not assume that the documented SysEx API is a full replacement for the Morningstar editor.

The published API is good enough for a stable, direct control layer, but it is clearly narrower than the editor feature set.

## Transport choice

Prefer a wired USB connection to the MC8 Pro `USB Device` port.

Relevant Morningstar notes:

- Port 1 is reserved for the editor path.
- The controller can expose multiple virtual USB MIDI ports.
- On Windows, the editor generally uses the lowest-valued port for the device.
- Large SysEx traffic can be problematic over some wireless adapters, which makes wired USB the safer path.

For our own direct tool, the safest policy is:

1. detect all Morningstar MC8 Pro input/output ports
2. identify Port 1 as the reserved editor port
3. use a different virtual port for our application when possible
4. if only Port 1 is available, require explicit confirmation before sharing the port with the editor

## Documented SysEx API surface

Morningstar's published SysEx API uses:

- manufacturer bytes: `00 21 24`
- Opcode 1 fixed at `0x70`
- MC8 Pro model ID: `0x08`

Base frame structure:

```text
F0 00 21 24 <model> 00 70 <op2> <op3> <op4> <op5> <op6> <op7> <txn> 00 00 <payload...> <checksum> F7
```

Checksum rule:

- XOR all bytes from `F0` through `n-2`
- mask with `0x7F`

Transaction IDs can be used to match replies to requests.

Error acknowledgement frame:

```text
F0 00 21 24 <model> 00 70 7F <ack> 00 00 00 00 <txn> 00 00 <checksum> F7
```

Ack codes:

- `00` success
- `01` wrong model id
- `02` wrong checksum
- `03` wrong payload size

## Documented functions worth implementing first

### Read-only probe layer

Start with read-only requests so we can validate port selection and framing safely.

- `op2 0x32` Get Controller Information
- `op2 0x30` Get Current Bank Name
- `op2 0x21` Get Preset Short Name
- `op2 0x22` Get Preset Toggle Name
- `op2 0x23` Get Preset Long Name
- `op2 0x31` Get toggle state of all presets in current bank

This should be the first real implementation milestone.

### Safe write layer

After readback works reliably, add narrow writes with clear response handling.

- `op2 0x01` Update Preset Short Name
- `op2 0x02` Update Preset Toggle Name
- `op2 0x03` Update Preset Long Name
- `op2 0x10` Update Current Bank Name
- `op2 0x11` Display message on LCD
- `op2 0x00` controller functions like bank up, bank down, toggle page

Morningstar documents a save-vs-override behavior for many write functions:

- `0x7F` in the save opcode field commits to memory
- other values act as temporary override and revert on bank change

That gives us a useful workflow distinction:

- non-destructive live overrides for testing
- explicit saved writes for committed changes

### Narrow preset-message editing layer

Morningstar also documents:

- `op2 0x04` Update Preset Message
- `op2 0x05` Update Preset Other Data

But the published `Update Preset Message` payloads are only documented for:

- `0x01` PC message
- `0x02` CC message

That means the documented direct-edit API is not a general editor-equivalent preset serializer.

## Minimal implementation plan

### Phase 1: transport and probes

Implement a small Python module that can:

- list Morningstar ports
- build request frames
- compute checksums
- send a SysEx request and wait for a matching response by transaction id
- decode ack frames and common read responses

Suggested first commands:

- `get_controller_info`
- `get_current_bank_name`
- `get_preset_short_name(bank_preset)`
- `get_preset_toggle_name(bank_preset)`
- `get_preset_long_name(bank_preset)`
- `get_toggle_states`

### Phase 2: safe writes

Implement:

- `set_current_bank_name(name, save)`
- `set_preset_short_name(preset, name, save)`
- `set_preset_toggle_name(preset, name, save)`
- `set_preset_long_name(preset, name, save)`
- `display_message(text, duration)`

### Phase 3: limited preset programming

Implement only what is actually documented:

- write preset message slot as PC
- write preset message slot as CC
- update preset other data such as toggle, blink, group, and PRO color fields

Anything beyond that should be treated as unverified.

## Why the documented SysEx API is not full editor parity

The editor manual and message-type manual expose a much larger configuration surface than the published SysEx API.

Documented editor/message-type capabilities include:

- up to 32 messages per switch preset
- many message families beyond PC and CC
- Note On/Off, Real Time, Song Position, Song Select, SysEx, MMC
- MIDI Clock and MIDI Clock Tap
- PC Number Scroll and CC Value Scroll
- Multi Engage/Bypass
- CC Waveform Generator
- Sequencer Generator
- Engage Preset and Trigger Messages
- Bank Change Mode and Bank Jump
- Toggle Preset and Set Toggle
- MIDI Thru, Select Expression Message, Looper Mode, Focus Mode
- Delay, Utility functions, Preset Rename, Relay Switching
- controller settings for Omniports, waveform engines, sequencer engines, scroll counters, MIDI channel mapping, and output masks
- bank and controller backup/restore
- global message parameter update
- preset save/load to JSON files

By contrast, the published SysEx API currently documents:

- controller navigation functions
- preset short/toggle/long name writes and reads
- current bank name write and read
- toggle-state read
- controller info read
- preset message writes only for PC and CC payload formats
- preset other-data writes for toggle/blink/group/colors

Notably absent from the published SysEx API:

- full preset readback
- full bank readback
- all-banks backup/restore protocol
- editor-profile data transport
- scroll counter configuration
- waveform engine configuration
- sequencer engine configuration
- MIDI channel remap/output-mask configuration
- general write support for the many message types available in the editor

This is the core reason to treat the documented SysEx API as a constrained integration layer rather than a full editor protocol.

## What this implies about the editor path

If the Morningstar editor can:

- back up all banks and controller settings
- restore all banks and settings
- edit controller-global structures like waveform engines, sequencer engines, scroll counters, MIDI channel routing, Omniports, and backup data
- author presets containing many message types beyond PC and CC

then at least one of these must be true:

1. the editor uses undocumented SysEx opcodes beyond the public page
2. the editor uses another transport alongside the published SysEx API
3. the public page is only a partial subset of the real wire protocol

Based on the docs, option 3 is the most likely.

The strongest evidence is simple: the editor feature surface is much larger than the published direct API surface.

## Best practical strategy

Use a two-track strategy.

### Track A: documented direct control

Build around the published SysEx API first.

This gives us:

- reliable controller detection
- stable request/response framing
- safe non-destructive probing
- direct naming and bank control
- limited PC/CC preset-message programming

This is the best short-term value.

### Track B: later editor-protocol discovery

If we later need full editor parity, the next move should be protocol discovery against official editor traffic, not browser or desktop UI automation.

That means capturing and comparing traffic for operations like:

- full preset save
- preset with non-PC/CC message types
- waveform engine edits
- sequencer engine edits
- controller backup and restore
- scroll counter edits
- MIDI channel routing edits

The likely outcome is a richer internal protocol than what is currently documented publicly.

## Recommended next code target

When the device is available, implement a new module for Morningstar similar in spirit to the existing Axe-Fx MIDI tooling, but separate from it.

Suggested future files:

- `morningstar_mc8_map.example.json` only if a higher-level command mapping becomes useful
- `tools/morningstar-mc8/` for probes and traffic captures

First live command to validate:

```text
Get Controller Information (op2 0x32)
```

If that round-trip works on the correct USB port, the transport foundation is sound.

## Morningstar MCP module

This workspace now includes a Morningstar MC8 Pro MCP server:

- `morningstar_mc8_mcp.py`

It currently exposes four practical capability groups.

### 1. Transport and probe tools

- MIDI port listing with Morningstar candidate detection
- SysEx framing reference for the documented MC8 Pro API
- `Get Controller Information`
- `Get Current Bank Name`
- `Get Preset Short Name`
- `Get Preset Toggle Name`
- `Get Preset Long Name`
- `Get Toggle States`

### 2. Direct write tools

- set current bank name
- set preset short name
- set preset toggle name
- set preset long name
- display a temporary LCD message
- bank up
- bank down
- toggle page
- write preset message slot as PC
- write preset message slot as CC
- write `CC0 + optional CC32 + PC` across adjacent slots

### 3. JSON-driven bank programming

- `program_current_bank_from_json`

This tool accepts a supported bank JSON shape and programs the currently selected bank in-place.

Supported inputs include:

- a compact program spec with `bank_name`, `presets`, and `messages`
- the generated Axe-Fx layout bank objects with `page_1` and `page_2`
- a compatible `bankData.bank` backup object

### 4. Draft backup JSON helpers

- `build_current_bank_backup_json`
- `build_all_banks_backup_json`
- `inspect_backup_json`

These tools build and inspect draft Morningstar-compatible backup containers from supported bank specs. They are intended for offline generation and reverse-engineering support, not yet for live restore.

### Experimental raw-message tools

- `set_preset_message_raw`
- `set_preset_message_note`

These exist so new message families can be tested without pretending we already have full editor-parity serializers. `set_preset_message_note` currently uses an inferred message-type id and should be treated as experimental until confirmed live.

Optional environment variables:

```env
MORNINGSTAR_MC8_MIDI_OUT=Exact MIDI output port name
MORNINGSTAR_MC8_MIDI_IN=Exact MIDI input port name
```

Run it with:

```powershell
python morningstar_mc8_mcp.py
```

When the controller is connected, the safest first live call is still:

```text
probe_get_controller_info
```

If multiple Morningstar virtual ports appear, pass the input and output port names explicitly and prefer a non-editor port where available.

## Current practical scope

The MCP is now good enough for:

- current-bank inspection
- current-bank naming updates
- preset label updates
- PC / CC / bank-select-plus-PC programming
- controller bank navigation and page toggling
- JSON-driven programming of the currently selected bank
- generation and inspection of draft bank and all-banks backup JSON

The MCP is still not a full replacement for the Morningstar editor.

Not yet implemented as live MCP tools:

- full editor message-family coverage beyond the documented PC/CC surface
- full-bank live readback
- all-banks restore to hardware
- controller-global settings writes
- profile switching/editing
- full editor backup/restore transport

## Current conclusion

The best move is:

1. use direct wired USB MIDI
2. build on the documented SysEx API first
3. keep scope limited to the documented read/write subset
4. treat full editor parity as a separate reverse-engineering task if and when needed

That gives the cleanest architecture with the least dependence on third-party UI layers.