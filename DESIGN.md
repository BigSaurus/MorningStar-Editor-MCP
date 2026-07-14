# Design and protocol notes

Background, reverse-engineering history, and the documented-SysEx reference for the Morningstar MC8 Pro
MCP server. This is context for contributors and the curious; you do not need any of it to install and
use the server (see `README.md`).

## Integration strategy

The server is built around direct, wired USB MIDI plus Morningstar's documented SysEx API as the primary
control path. That choice avoids WebMIDI/browser permission problems and UI automation against the web or
desktop editor, and it gives deterministic request/response control over a documented transport.

The documented SysEx API is a good, stable, direct control layer, but it is narrower than the full editor
feature set. Full editor parity is treated as a separate reverse-engineering task, tackled only where a
capability is actually needed (this is how the persistent flash-write path came to exist).

## Transport and port selection

Prefer a wired USB connection to the MC8 Pro `USB Device` port.

- Port 1 is reserved for the editor path.
- The controller can expose multiple virtual USB MIDI ports.
- On Windows, the editor generally uses the lowest-valued port for the device.
- Large SysEx traffic can be problematic over some wireless adapters, so wired USB is the safer path.

Port policy the server follows:

1. detect all Morningstar MC8 Pro input/output ports
2. treat Port 1 as the reserved editor port
3. prefer a different virtual port for direct probe/write traffic when possible
4. the group-7 flash-upload protocol specifically runs on the primary port pair (cable 0)

## Documented SysEx API surface

Morningstar's published SysEx API uses:

- manufacturer bytes: `00 21 24`
- Opcode 1 fixed at `0x70`
- MC8 Pro model ID: `0x08`

Base frame structure:

```text
F0 00 21 24 <model> 00 70 <op2> <op3> <op4> <op5> <op6> <op7> <txn> 00 00 <payload...> <checksum> F7
```

Checksum rule: XOR all bytes from `F0` through `n-2`, then mask with `0x7F`. Transaction IDs match replies
to requests.

Error acknowledgement frame:

```text
F0 00 21 24 <model> 00 70 7F <ack> 00 00 00 00 <txn> 00 00 <checksum> F7
```

Ack codes: `00` success, `01` wrong model id, `02` wrong checksum, `03` wrong payload size.

### Read-only probe layer

- `op2 0x32` Get Controller Information
- `op2 0x30` Get Current Bank Name
- `op2 0x21` Get Preset Short Name
- `op2 0x22` Get Preset Toggle Name
- `op2 0x23` Get Preset Long Name
- `op2 0x31` Get toggle state of all presets in current bank

### Safe write layer

- `op2 0x01` Update Preset Short Name
- `op2 0x02` Update Preset Toggle Name
- `op2 0x03` Update Preset Long Name
- `op2 0x10` Update Current Bank Name
- `op2 0x11` Display message on LCD
- `op2 0x00` controller functions such as bank up, bank down, toggle page

Morningstar documents a save-vs-override behavior for many write functions: `0x7F` in the save opcode
field commits to the working bank buffer; other values act as a temporary override that reverts on bank
change. Important: `0x7F` here is **working memory only** — these `0x70` writes do **not** survive a
power-cycle. Committing to flash requires the group-7 upload path (see README, "Persistent bank writes").

### Narrow preset-message editing layer

- `op2 0x04` Update Preset Message
- `op2 0x05` Update Preset Other Data

The published `Update Preset Message` payloads are documented only for `0x01` (PC) and `0x02` (CC), so the
documented direct-edit API is not a general editor-equivalent preset serializer.

## Why the documented API is not full editor parity

The editor and message-type manuals expose a much larger configuration surface than the published SysEx
API: up to 32 messages per switch preset; many message families beyond PC and CC (Note On/Off, Real Time,
Song Position/Select, SysEx, MMC, MIDI Clock and Tap, PC/CC scroll, Multi Engage/Bypass, waveform and
sequencer generators, engage/trigger, bank change/jump, toggle/set, MIDI Thru, expression select, looper,
focus, delay/utility, relay switching); controller-global settings (Omniports, waveform/sequencer engines,
scroll counters, MIDI channel mapping, output masks); and full bank/controller backup and restore.

The published SysEx API, by contrast, documents controller navigation, short/toggle/long name and current
bank name read/write, toggle-state and controller-info reads, and preset message writes only for PC and
CC. Notably absent: full preset/bank readback, all-banks backup/restore, editor-profile transport, and
general write support for the many editor message types.

The most likely explanation is that the public page is a partial subset of the real wire protocol — the
editor uses undocumented opcodes over the same USB MIDI transport. That prediction is what motivated the
editor-protocol capture work.

## Editor-protocol discovery (group-7 upload)

Full editor parity requires protocol discovery against real editor traffic rather than UI automation. A
USB capture of a real editor **all-banks restore** revealed the undocumented **group-7 upload protocol**
(connect handshake, request/ACK chunk streaming, flash commit) running over USB MIDI. It is implemented
for persistent bank/preset writes; see the README's "Persistent bank writes" section for usage.

Still open for future capture/decode work:

- presets with non-PC/CC message types
- waveform engine edits
- sequencer engine edits
- controller-settings (Omniport/aux/clock) backup and restore
- scroll counter edits
- MIDI channel routing edits

## Roadmap notes

- Higher-level command mapping (e.g. a `morningstar-mc8-map` JSON) only if it proves useful.
- Deeper controller-global settings coverage as captures are decoded.
- The draft `controllerData` helpers currently model two inferred aux topologies (Omniport 1
  resistor-ladder aux switches via `aux_switch`, and TRS aux slots via `omniport` + `slot`). These are
  backup-generation drafts, not proven live restore payloads.
