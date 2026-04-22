# MC8 MCP Tool Reference

This file is generated from `morningstar_mc8_mcp.py`. It documents the regular MCP tool surface exposed by the Morningstar MC8 Pro server without introducing a custom API layer.

## Server Status

- Runtime model: regular MCP server over stdio
- Primary server file: `morningstar_mc8_mcp.py`
- Tool count: 25
- Validated Windows ports in this workspace: output `Morningstar MC8 Pro 3`, input `Morningstar MC8 Pro 2`

## Categories

- Discovery and Protocol: 2 tools
- Read Probes: 6 tools
- Name and UI Writes: 5 tools
- Navigation: 3 tools
- Preset Message Programming: 5 tools
- Bank Programming: 1 tools
- Offline Backup JSON: 3 tools

## Safety Levels

- `read-only`: queries device state without modifying controller data
- `write`: updates controller state or persistent data
- `navigation`: changes the current controller view or bank selection
- `experimental`: write surface exists, but parts of the protocol remain inferred or lightly verified
- `offline-json`: transforms backup JSON locally without device I/O

## Transport Notes

- `request-response`: sends a SysEx request and waits for a matching reply or ACK
- `fire-and-forget`: sends a controller command without waiting for an ACK
- `mixed`: performs writes plus optional follow-up probe reads
- `local-only`: performs no device I/O

## Recommended Workflows

### 1. Confirm ports, then read the active bank

```python
list_midi_ports()
probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

Use this path first when a session starts. It confirms which virtual ports are available and gives you a safe readback anchor before any navigation or writes.

### 2. Test a label change without saving it

```python
set_current_bank_name(bank_name='TEST BANK', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

Use temporary overrides when validating framing, port selection, or naming logic. Unsaved names revert on bank change.

### 3. Program the selected bank from JSON and verify it

```python
program_current_bank_from_json(bank_json='{"bank_name":"AFX 001-008","presets":[]}', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2', midi_channel=1, verify=True)
```

This is the highest-level live programming workflow in the current MCP surface. Keep `verify=True` unless you already have a faster external verification loop.

### 4. Build and inspect backup JSON offline

```python
build_current_bank_backup_json(bank_json='{"bank_name":"AFX 001-008","presets":[]}', pretty=True)
inspect_backup_json(backup_json='{}')
```

Use the offline backup helpers when you need Morningstar-shaped JSON containers without touching the device.

### 5. Navigate one bank, then verify the move

```python
before = probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
bank_up(output_port='Morningstar MC8 Pro 3')
after = probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

Navigation calls are fire-and-forget in this setup, so use a follow-up bank-name read to confirm the controller actually moved.

### 6. Write a preset message slot and read back a nearby label

```python
set_preset_message_cc(preset='A', message_slot=0, cc_number=34, cc_value=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
probe_get_preset_short_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

Message writes do not have a full readback surface today, so pair them with adjacent observable checks such as bank-name or preset-label reads.

## Discovery and Protocol

### `list_midi_ports`

Report the MIDI ports visible to this host and highlight likely Morningstar candidates.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `local-only`
- Returns: Lists MIDI inputs, outputs, Morningstar candidates, and configured defaults.

**Signature**

```python
list_midi_ports() -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |

**Notes**

- Does not talk to the controller.
- Use this first when multiple Morningstar ports are visible.

**Example**

```python
list_midi_ports()
```

### `get_sysex_reference`

Return the SysEx framing constants and capability summary that this MCP server is built around.

- Safety: `read-only`
- Verification: `source-backed`
- Transport: `local-only`
- Returns: Returns the framing constants, ack codes, and documented read-only capability summary used by this server.

**Signature**

```python
get_sysex_reference() -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |

**Notes**

- Does not talk to the controller.

**Example**

```python
get_sysex_reference()
```

## Read Probes

### `probe_get_controller_info`

Query controller identity and limits so you can verify the device and payload sizes before writing.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus decoded controller model, firmware, and name-size limits.

**Signature**

```python
probe_get_controller_info(output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 1) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `1` |

**Notes**

- Useful for validating framing and firmware assumptions before writes.

**Example**

```python
probe_get_controller_info(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `probe_get_current_bank_name`

Read the name of the bank that is currently selected on the controller.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus decoded current bank name.

**Signature**

```python
probe_get_current_bank_name(output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 2) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `2` |

**Notes**

- Primary readback used to verify bank navigation and bank programming.

**Example**

```python
probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `probe_get_preset_short_name`

Read the short label for one preset in the currently selected bank. Preset A maps to slot 0.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus decoded preset short name for the current bank.

**Signature**

```python
probe_get_preset_short_name(preset: str, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 3) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `3` |

**Notes**

- Preset labels accept letters such as A through P on MC8 Pro.

**Example**

```python
probe_get_preset_short_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `probe_get_preset_toggle_name`

Read the toggle label for one preset in the currently selected bank. Preset A maps to slot 0.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus decoded preset toggle name for the current bank.

**Signature**

```python
probe_get_preset_toggle_name(preset: str, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 4) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `4` |

**Example**

```python
probe_get_preset_toggle_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `probe_get_preset_long_name`

Read the long label for one preset in the currently selected bank. Preset A maps to slot 0.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus decoded preset long name for the current bank.

**Signature**

```python
probe_get_preset_long_name(preset: str, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 5) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `5` |

**Example**

```python
probe_get_preset_long_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `probe_get_toggle_states`

Read the toggle-state bytes for every preset in the currently selected bank.

- Safety: `read-only`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns toggle-state bytes for the current bank plus a decoded per-preset view.

**Signature**

```python
probe_get_toggle_states(output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 6) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `6` |

**Example**

```python
probe_get_toggle_states(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

## Name and UI Writes

### `set_current_bank_name`

Rename the current bank, either as a saved edit or as a temporary override that clears on bank change.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded echo of the target bank name and save mode.

**Signature**

```python
set_current_bank_name(bank_name: str, save: bool = True, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 20) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `bank_name` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `20` |

**Notes**

- save=False applies a temporary override that reverts on bank change.

**Example**

```python
set_current_bank_name(bank_name='AFX 001-008', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_short_name`

Update one preset's short label in the current bank.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded echo of the target short name.

**Signature**

```python
set_preset_short_name(preset: str, short_name: str, save: bool = True, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 21) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `short_name` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `21` |

**Notes**

- save=False applies a temporary override that reverts on bank change.

**Example**

```python
set_preset_short_name(preset='A', short_name='RECTO 1', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_toggle_name`

Update one preset's toggle label in the current bank.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded echo of the target toggle name.

**Signature**

```python
set_preset_toggle_name(preset: str, toggle_name: str, save: bool = True, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 22) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `toggle_name` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `22` |

**Notes**

- save=False applies a temporary override that reverts on bank change.

**Example**

```python
set_preset_toggle_name(preset='A', toggle_name='Drive On', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_long_name`

Update one preset's long label in the current bank.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded echo of the target long name.

**Signature**

```python
set_preset_long_name(preset: str, long_name: str, save: bool = True, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 23) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `long_name` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `23` |

**Notes**

- save=False applies a temporary override that reverts on bank change.

**Example**

```python
set_preset_long_name(preset='A', long_name='Recto Rhythm', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `display_message`

Show a temporary message on the MC8 display without changing stored bank data.

- Safety: `write`
- Verification: `live-verified`
- Transport: `fire-and-forget`
- Returns: Returns the encoded request summary and decoded display duration actually sent.

**Signature**

```python
display_message(message: str, duration_ms: int = 1000, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 24) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `message` | `str` | yes | `` |
| `duration_ms` | `int` | no | `1000` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `24` |

**Notes**

- This server does not wait for an ACK for display_message in this setup.
- The message length limit is enforced as ASCII up to 20 characters.

**Example**

```python
display_message(message='Bank loaded', duration_ms=1000, output_port='Morningstar MC8 Pro 3')
```

## Navigation

### `bank_up`

Advance the controller to the next bank using Morningstar's bank-up function.

- Safety: `navigation`
- Verification: `live-verified`
- Transport: `fire-and-forget`
- Returns: Returns the encoded request summary and decoded function name.

**Signature**

```python
bank_up(output_port: str = '', txn_id: int = 40) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `txn_id` | `int` | no | `40` |

**Notes**

- Does not wait for an ACK.
- Use bank-name readback to verify motion after sending.

**Example**

```python
bank_up(output_port='Morningstar MC8 Pro 3')
```

### `bank_down`

Move the controller to the previous bank using Morningstar's bank-down function.

- Safety: `navigation`
- Verification: `live-verified`
- Transport: `fire-and-forget`
- Returns: Returns the encoded request summary and decoded function name.

**Signature**

```python
bank_down(output_port: str = '', txn_id: int = 41) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `txn_id` | `int` | no | `41` |

**Notes**

- Does not wait for an ACK.
- Use bank-name readback to verify motion after sending.

**Example**

```python
bank_down(output_port='Morningstar MC8 Pro 3')
```

### `toggle_page`

Toggle between the controller's page views for the current bank.

- Safety: `navigation`
- Verification: `live-verified`
- Transport: `fire-and-forget`
- Returns: Returns the encoded request summary and decoded function name.

**Signature**

```python
toggle_page(output_port: str = '', txn_id: int = 42) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `output_port` | `str` | no | `''` |
| `txn_id` | `int` | no | `42` |

**Notes**

- Does not wait for an ACK.
- Use a follow-up preset-name read if page-specific labels matter.

**Example**

```python
toggle_page(output_port='Morningstar MC8 Pro 3')
```

## Preset Message Programming

### `set_preset_message_raw`

Write a raw preset-message payload when no safer typed helper exists.

- Safety: `experimental`
- Verification: `partially-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded summary of the raw message write.

**Signature**

```python
set_preset_message_raw(preset: str, message_slot: int, message_type: int, payload_json: str, save: bool = True, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 33) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `message_slot` | `int` | yes | `` |
| `message_type` | `int` | yes | `` |
| `payload_json` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `33` |

**Notes**

- Use this only when a typed wrapper does not exist.
- payload_json must decode to a JSON array of 7-bit integers.

**Example**

```python
set_preset_message_raw(preset='A', message_slot=0, message_type=3, payload_json='[1,0,60,100,0]', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_message_note`

Write an inferred Note message through the experimental raw-message path. Treat the message-type mapping as unverified.

- Safety: `experimental`
- Verification: `partially-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded summary of the inferred note-message write.

**Signature**

```python
set_preset_message_note(preset: str, message_slot: int, note_number: int, velocity: int, midi_channel: int, save: bool = True, action_type: int = 1, toggle_type: int = 0, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 34) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `message_slot` | `int` | yes | `` |
| `note_number` | `int` | yes | `` |
| `velocity` | `int` | yes | `` |
| `midi_channel` | `int` | yes | `` |
| `save` | `bool` | no | `True` |
| `action_type` | `int` | no | `1` |
| `toggle_type` | `int` | no | `0` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `34` |

**Notes**

- Message type 0x03 is inferred from editor ordering and remains unverified.

**Example**

```python
set_preset_message_note(preset='A', message_slot=0, note_number=60, velocity=100, midi_channel=0, save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_message_pc`

Write one documented Program Change message into a preset message slot.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded summary of the Program Change write.

**Signature**

```python
set_preset_message_pc(preset: str, message_slot: int, program: int, midi_channel: int, save: bool = True, action_type: int = 1, toggle_type: int = 0, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 30) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `message_slot` | `int` | yes | `` |
| `program` | `int` | yes | `` |
| `midi_channel` | `int` | yes | `` |
| `save` | `bool` | no | `True` |
| `action_type` | `int` | no | `1` |
| `toggle_type` | `int` | no | `0` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `30` |

**Notes**

- midi_channel is zero-based because it maps directly to Morningstar's wire format.

**Example**

```python
set_preset_message_pc(preset='A', message_slot=0, program=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_message_cc`

Write one documented Control Change message into a preset message slot.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns the raw response plus a decoded summary of the Control Change write.

**Signature**

```python
set_preset_message_cc(preset: str, message_slot: int, cc_number: int, cc_value: int, midi_channel: int, save: bool = True, action_type: int = 1, toggle_type: int = 0, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 31) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `message_slot` | `int` | yes | `` |
| `cc_number` | `int` | yes | `` |
| `cc_value` | `int` | yes | `` |
| `midi_channel` | `int` | yes | `` |
| `save` | `bool` | no | `True` |
| `action_type` | `int` | no | `1` |
| `toggle_type` | `int` | no | `0` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `31` |

**Notes**

- midi_channel is zero-based because it maps directly to Morningstar's wire format.

**Example**

```python
set_preset_message_cc(preset='A', message_slot=0, cc_number=34, cc_value=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

### `set_preset_bank_select_and_program_change`

Write CC0, optional CC32, and Program Change into adjacent slots for one preset.

- Safety: `write`
- Verification: `live-verified`
- Transport: `request-response`
- Returns: Returns a combined summary of the adjacent CC0, optional CC32, and PC writes.

**Signature**

```python
set_preset_bank_select_and_program_change(preset: str, start_message_slot: int, bank_msb: int, program: int, midi_channel: int, save: bool = True, include_bank_lsb: bool = False, bank_lsb: int = 0, action_type: int = 1, toggle_type: int = 0, output_port: str = '', input_port: str = '', timeout_ms: int = 600, txn_id: int = 32) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `preset` | `str` | yes | `` |
| `start_message_slot` | `int` | yes | `` |
| `bank_msb` | `int` | yes | `` |
| `program` | `int` | yes | `` |
| `midi_channel` | `int` | yes | `` |
| `save` | `bool` | no | `True` |
| `include_bank_lsb` | `bool` | no | `False` |
| `bank_lsb` | `int` | no | `0` |
| `action_type` | `int` | no | `1` |
| `toggle_type` | `int` | no | `0` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `timeout_ms` | `int` | no | `600` |
| `txn_id` | `int` | no | `32` |

**Notes**

- Requires adjacent message slots.
- The highest valid start_message_slot is 14 for CC0 plus PC, or 13 when include_bank_lsb=True.

**Example**

```python
set_preset_bank_select_and_program_change(preset='A', start_message_slot=0, bank_msb=0, program=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')
```

## Bank Programming

### `program_current_bank_from_json`

Program the currently selected bank from a supported JSON spec and optionally verify the result with live readback.

- Safety: `write`
- Verification: `live-verified`
- Transport: `mixed`
- Returns: Writes the selected bank from a supported JSON spec and optionally verifies bank name plus preset A readback.

**Signature**

```python
program_current_bank_from_json(bank_json: str, save: bool = True, output_port: str = '', input_port: str = '', midi_channel: int = 1, verify: bool = True) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `bank_json` | `str` | yes | `` |
| `save` | `bool` | no | `True` |
| `output_port` | `str` | no | `''` |
| `input_port` | `str` | no | `''` |
| `midi_channel` | `int` | no | `1` |
| `verify` | `bool` | no | `True` |

**Notes**

- midi_channel is one-based here and converted internally before writing message payloads.
- verify=True performs follow-up probe reads against the device.

**Example**

```python
program_current_bank_from_json(bank_json='{"bank_name":"AFX 001-008","presets":[]}', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2', midi_channel=1, verify=False)
```

## Offline Backup JSON

### `build_current_bank_backup_json`

Build a draft current-bank backup JSON wrapper locally from a supported bank spec.

- Safety: `offline-json`
- Verification: `source-backed`
- Transport: `local-only`
- Returns: Builds a draft current-bank backup container and returns it as a JSON string.

**Signature**

```python
build_current_bank_backup_json(bank_json: str, bank_number: int = 0, profile_number: int = 0, model_id: int = 8, pretty: bool = True) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `bank_json` | `str` | yes | `` |
| `bank_number` | `int` | no | `0` |
| `profile_number` | `int` | no | `0` |
| `model_id` | `int` | no | `8` |
| `pretty` | `bool` | no | `True` |

**Notes**

- Does not talk to the controller.

**Example**

```python
build_current_bank_backup_json(bank_json='{"bank_name":"AFX 001-008","presets":[]}', pretty=True)
```

### `build_all_banks_backup_json`

Build a draft all-banks backup JSON container locally, with optional controllerData content.

- Safety: `offline-json`
- Verification: `source-backed`
- Transport: `local-only`
- Returns: Builds a draft all-banks backup container with optional controllerData.

**Signature**

```python
build_all_banks_backup_json(banks_json: str, controller_data_json: str = '{}', pretty: bool = True) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `banks_json` | `str` | yes | `` |
| `controller_data_json` | `str` | no | `'{}'` |
| `pretty` | `bool` | no | `True` |

**Notes**

- Does not talk to the controller.
- Accepts either bank specs or already wrapped bank backup objects.

**Example**

```python
build_all_banks_backup_json(banks_json='[]', controller_data_json='{}', pretty=True)
```

### `inspect_backup_json`

Inspect a Morningstar-style backup JSON blob and summarize its bank and controller-data structure.

- Safety: `offline-json`
- Verification: `source-backed`
- Transport: `local-only`
- Returns: Inspects a draft backup blob and returns a summary of banks, arrangements, and controllerData presence.

**Signature**

```python
inspect_backup_json(backup_json: str) -> dict[str, typing.Any]
```

**Parameters**

| Name | Type | Required | Default |
| --- | --- | --- | --- |
| `backup_json` | `str` | yes | `` |

**Notes**

- Does not talk to the controller.

**Example**

```python
inspect_backup_json(backup_json='{}')
```
