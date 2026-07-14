import copy
import inspect
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

try:
    import mido
except Exception as ex:  # noqa: BLE001
    raise RuntimeError(
        "mido is required. Install dependencies with: pip install -r requirements.txt"
    ) from ex


load_dotenv()

mcp = FastMCP("morningstar-mc8-mcp")


DEFAULT_OUT_PORT = os.getenv("MORNINGSTAR_MC8_MIDI_OUT", "")
DEFAULT_IN_PORT = os.getenv("MORNINGSTAR_MC8_MIDI_IN", "")

MORNINGSTAR_MANUFACTURER_ID = [0x00, 0x21, 0x24]
MC8_PRO_MODEL_ID = 0x08
MORNINGSTAR_OPCODE_1 = 0x70
DEFAULT_TIMEOUT_MS = 600

ACK_CODES = {
    0x00: "SUCCESS",
    0x01: "WRONG MODEL ID",
    0x02: "WRONG CHECKSUM",
    0x03: "WRONG PAYLOAD SIZE",
}

MC8_PRO_SHORT_NAME_SIZE = 32
MC8_PRO_TOGGLE_NAME_SIZE = 32
MC8_PRO_LONG_NAME_SIZE = 32
MC8_PRO_BANK_NAME_SIZE = 32
MC8_PRO_LCD_MESSAGE_SIZE = 20
MC8_PRO_OMNIPORT_COUNT = 4
MC8_PRO_EXP_PRESET_COUNT = 2
MC8_PRO_PRESET_MESSAGE_COUNT = 32
MC8_PRO_RESISTOR_LADDER_AUX_SWITCH_COUNT = 16
REQUEST_CONTROLLER_SETTINGS_ALL = 35
REQUEST_OMNIPORT_DATA = 42
CONTROLLER_SETTINGS_WRITE_OPCODE_2 = 0x04
WRITE_CONTROLLER_OMNIPORT_DATA = 0x08
WRITE_CONTROLLER_EVENT_PROCESSOR_DATA = 0x0A
WRITE_RESISTOR_LADDER_AUX_SWITCH_DATA = 0x0B
WRITE_MIDI_CLOCK_SLOTS_DATA = 0x0C

ACTION_TYPE_PRESS = 0x01
TOGGLE_TYPE_POS_1 = 0x00
MESSAGE_TYPE_PC = 0x01
MESSAGE_TYPE_CC = 0x02
CONTROLLER_FUNCTION_BANK_UP = 0x00
CONTROLLER_FUNCTION_BANK_DOWN = 0x01
CONTROLLER_FUNCTION_TOGGLE_PAGE = 0x04
EDITOR_UPLOAD_OPCODE_2 = 0x07
EDITOR_UPLOAD_START_OPCODE_4 = 0x30
EDITOR_UPLOAD_START_ALL_OPCODE_4 = 0x31
EDITOR_UPLOAD_FINALIZE_OPCODE_4 = 0x31
EDITOR_UPLOAD_REQUEST_BACKUP_OPCODE_4 = 0x32
EDITOR_UPLOAD_BANK_OPCODE_3 = 0x10
EDITOR_UPLOAD_PRESET_OPCODE_3 = 0x11
EDITOR_UPLOAD_EXP_PRESET_OPCODE_3 = 0x12
EDITOR_UPLOAD_ALL_BANK_OPCODE_3 = 0x13
EDITOR_UPLOAD_ALL_PRESET_OPCODE_3 = 0x14
EDITOR_UPLOAD_ALL_EXP_PRESET_OPCODE_3 = 0x15
EDITOR_UPLOAD_STATUS_FAILED = 0x03
EDITOR_UPLOAD_STATUS_CONTROLLER_BACKUP_FAILED = 0x10
EDITOR_UPLOAD_STATUS_COMPLETED = 0x11
EDITOR_UPLOAD_STATUS_REQUEST_NEXT = 0x21
MAX_RAW_MESSAGE_PAYLOAD_SIZE = 64
MESSAGE_JSON_DATA_FIELD_COUNT = 18
MC8_PRO_PRESET_COUNT = 16
MC8_PRO_EDITOR_UPLOAD_PRESET_COUNT = 24
MC8_PRO_EDITOR_UPLOAD_EXP_PRESET_COUNT = 4
# Editor connect handshake (over USB-MIDI cable 0) that opens the group-7 upload session.
# (function_1, function_2, function_3, model_id) - reverse-engineered from a USBPcap capture.
EDITOR_CONNECT_SEQUENCE = [
    (0, 28, 0, MC8_PRO_MODEL_ID),
    (3, 49, 0, MC8_PRO_MODEL_ID),
    (0, 27, 0, 0x00),
    (0, 44, 0, MC8_PRO_MODEL_ID),
    (3, 49, 0, MC8_PRO_MODEL_ID),
    (0, 64, 2, MC8_PRO_MODEL_ID),
]
EDITOR_ACK_FUNCTION_2 = 0x7F  # host acks each received frame: func(0, 127, <frame checksum>)
DRAFT_CONTROLLER_DATA_VERSION = "draft-inferred-v2"

SUPPORTED_AUX_TOPOLOGIES = {
    "resistor_ladder_aux",
    "trs_aux",
}

SUPPORTED_TRS_AUX_SLOTS = {
    "tip": "tip",
    "ring": "ring",
    "tip+ring": "tip_ring",
    "tip_ring": "tip_ring",
    "tip-ring": "tip_ring",
}

SUPPORTED_AUX_FIXED_FUNCTIONS = {
    "bank_up",
    "bank_down",
    "toggle_page",
    "midi_clock_tap",
}

READ_ONLY_CAPABILITIES: dict[str, Any] = {
    "summary": {
        "scope": "Morningstar MC8 Pro documented read-only probe layer",
        "transport": "USB MIDI SysEx",
        "model_id": MC8_PRO_MODEL_ID,
        "opcode_1": MORNINGSTAR_OPCODE_1,
    },
    "implemented_tools": [
        "list_midi_ports",
        "get_sysex_reference",
        "probe_get_controller_info",
        "probe_get_current_bank_name",
        "probe_get_preset_short_name",
        "probe_get_preset_toggle_name",
        "probe_get_preset_long_name",
        "probe_get_toggle_states",
    ],
    "notes": [
        "This server intentionally avoids write functions.",
        "Prefer a non-editor virtual MIDI port when the controller exposes multiple ports.",
        "Pass output_port and input_port explicitly when multiple Morningstar ports are present.",
    ],
}

TOOL_REFERENCE_GROUP_ORDER = [
    "Discovery and Protocol",
    "Read Probes",
    "Controller Settings",
    "Name and UI Writes",
    "Navigation",
    "Preset Message Programming",
    "Bank Programming",
    "Offline Backup JSON",
]

TOOL_REFERENCE_METADATA: dict[str, dict[str, Any]] = {
    "list_midi_ports": {
        "group": "Discovery and Protocol",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "local-only",
        "returns": "Lists MIDI inputs, outputs, Morningstar candidates, and configured defaults.",
        "notes": [
            "Does not talk to the controller.",
            "Use this first when multiple Morningstar ports are visible.",
        ],
        "example": 'list_midi_ports()',
    },
    "get_sysex_reference": {
        "group": "Discovery and Protocol",
        "safety": "read-only",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Returns the framing constants, ack codes, and documented read-only capability summary used by this server.",
        "notes": [
            "Does not talk to the controller.",
        ],
        "example": 'get_sysex_reference()',
    },
    "probe_get_controller_info": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus decoded controller model, firmware, and name-size limits.",
        "notes": [
            "Useful for validating framing and firmware assumptions before writes.",
        ],
        "example": "probe_get_controller_info(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_current_bank_name": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus decoded current bank name.",
        "notes": [
            "Primary readback used to verify bank navigation and bank programming.",
        ],
        "example": "probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_preset_short_name": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus decoded preset short name for the current bank.",
        "notes": [
            "Preset labels accept letters such as A through P on MC8 Pro.",
        ],
        "example": "probe_get_preset_short_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_preset_toggle_name": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus decoded preset toggle name for the current bank.",
        "notes": [],
        "example": "probe_get_preset_toggle_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_preset_long_name": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus decoded preset long name for the current bank.",
        "notes": [],
        "example": "probe_get_preset_long_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_toggle_states": {
        "group": "Read Probes",
        "safety": "read-only",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns toggle-state bytes for the current bank plus a decoded per-preset view.",
        "notes": [],
        "example": "probe_get_toggle_states(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_controller_settings_all": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Returns the raw controller-settings-all response using the editor-backed request opcode.",
        "notes": [
            "The response payload shape is not decoded yet.",
        ],
        "example": "probe_get_controller_settings_all(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "probe_get_controller_omniport_data": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Returns the raw Omniport controller-settings response using the editor-backed request opcode.",
        "notes": [
            "The response payload shape is not decoded yet.",
        ],
        "example": "probe_get_controller_omniport_data(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_controller_omniport_data_raw": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Writes a raw Omniport controller-settings payload using the editor-backed save opcode.",
        "notes": [
            "payload_json must decode to a JSON array of 7-bit integers.",
            "This exposes transport only; the payload schema remains inferred.",
        ],
        "example": "set_controller_omniport_data_raw(payload_json='[]', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_controller_event_processor_raw": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Writes a raw event-processor payload using the editor-backed save opcode.",
        "notes": [
            "payload_json must decode to a JSON array of 7-bit integers.",
            "The editor sends this path as sendSysex4(4,10,0,0,payload).",
        ],
        "example": "set_controller_event_processor_raw(payload_json='[]', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_controller_resistor_ladder_aux_raw": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Writes a raw resistor-ladder aux payload using the editor-backed save opcode.",
        "notes": [
            "payload_json must decode to a JSON array of 7-bit integers.",
            "This is the most direct live transport slice for AUX 1-4 once the payload layout is captured.",
        ],
        "example": "set_controller_resistor_ladder_aux_raw(payload_json='[]', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_controller_midi_clock_slots_raw": {
        "group": "Controller Settings",
        "safety": "experimental",
        "verification": "source-backed",
        "transport": "request-response",
        "returns": "Writes a raw MIDI clock slots payload using the editor-backed save opcode.",
        "notes": [
            "payload_json must decode to a JSON array of 7-bit integers.",
        ],
        "example": "set_controller_midi_clock_slots_raw(payload_json='[]', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_current_bank_name": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded echo of the target bank name and save mode.",
        "notes": [
            "save=False applies a temporary override that reverts on bank change; even save=True is RAM-only and is LOST on power-cycle. For permanent (flash) storage, generate a file with build_editor_native_restore_file and import it in the official editor.",
        ],
        "example": "set_current_bank_name(bank_name='AFX 001-008', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_short_name": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded echo of the target short name.",
        "notes": [
            "save=False applies a temporary override that reverts on bank change; even save=True is RAM-only and is LOST on power-cycle. For permanent (flash) storage, generate a file with build_editor_native_restore_file and import it in the official editor.",
        ],
        "example": "set_preset_short_name(preset='A', short_name='RECTO 1', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_toggle_name": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded echo of the target toggle name.",
        "notes": [
            "save=False applies a temporary override that reverts on bank change; even save=True is RAM-only and is LOST on power-cycle. For permanent (flash) storage, generate a file with build_editor_native_restore_file and import it in the official editor.",
        ],
        "example": "set_preset_toggle_name(preset='A', toggle_name='Drive On', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_long_name": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded echo of the target long name.",
        "notes": [
            "save=False applies a temporary override that reverts on bank change; even save=True is RAM-only and is LOST on power-cycle. For permanent (flash) storage, generate a file with build_editor_native_restore_file and import it in the official editor.",
        ],
        "example": "set_preset_long_name(preset='A', long_name='Recto Rhythm', save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "display_message": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "fire-and-forget",
        "returns": "Returns the encoded request summary and decoded display duration actually sent.",
        "notes": [
            "This server does not wait for an ACK for display_message in this setup.",
            "The message length limit is enforced as ASCII up to 20 characters.",
        ],
        "example": "display_message(message='Bank loaded', duration_ms=1000, output_port='Morningstar MC8 Pro 3')",
    },
    "bank_up": {
        "group": "Navigation",
        "safety": "navigation",
        "verification": "live-verified",
        "transport": "fire-and-forget",
        "returns": "Returns the encoded request summary and decoded function name.",
        "notes": [
            "Does not wait for an ACK.",
            "Use bank-name readback to verify motion after sending.",
        ],
        "example": "bank_up(output_port='Morningstar MC8 Pro 3')",
    },
    "bank_down": {
        "group": "Navigation",
        "safety": "navigation",
        "verification": "live-verified",
        "transport": "fire-and-forget",
        "returns": "Returns the encoded request summary and decoded function name.",
        "notes": [
            "Does not wait for an ACK.",
            "Use bank-name readback to verify motion after sending.",
        ],
        "example": "bank_down(output_port='Morningstar MC8 Pro 3')",
    },
    "toggle_page": {
        "group": "Navigation",
        "safety": "navigation",
        "verification": "live-verified",
        "transport": "fire-and-forget",
        "returns": "Returns the encoded request summary and decoded function name.",
        "notes": [
            "Does not wait for an ACK.",
            "Use a follow-up preset-name read if page-specific labels matter.",
        ],
        "example": "toggle_page(output_port='Morningstar MC8 Pro 3')",
    },
    "set_preset_message_raw": {
        "group": "Preset Message Programming",
        "safety": "experimental",
        "verification": "partially-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded summary of the raw message write.",
        "notes": [
            "Use this only when a typed wrapper does not exist.",
            "payload_json must decode to a JSON array of 7-bit integers.",
        ],
        "example": "set_preset_message_raw(preset='A', message_slot=0, message_type=3, payload_json='[1,0,60,100,0]', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_message_note": {
        "group": "Preset Message Programming",
        "safety": "experimental",
        "verification": "partially-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded summary of the inferred note-message write.",
        "notes": [
            "Message type 0x03 is inferred from editor ordering and remains unverified.",
        ],
        "example": "set_preset_message_note(preset='A', message_slot=0, note_number=60, velocity=100, midi_channel=0, save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_message_pc": {
        "group": "Preset Message Programming",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded summary of the Program Change write.",
        "notes": [
            "midi_channel is zero-based because it maps directly to Morningstar's wire format.",
        ],
        "example": "set_preset_message_pc(preset='A', message_slot=0, program=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_message_cc": {
        "group": "Preset Message Programming",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded summary of the Control Change write.",
        "notes": [
            "midi_channel is zero-based because it maps directly to Morningstar's wire format.",
        ],
        "example": "set_preset_message_cc(preset='A', message_slot=0, cc_number=34, cc_value=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "set_preset_bank_select_and_program_change": {
        "group": "Preset Message Programming",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns a combined summary of the adjacent CC0, optional CC32, and PC writes.",
        "notes": [
            "Requires adjacent message slots.",
            "The highest valid start_message_slot is 14 for CC0 plus PC, or 13 when include_bank_lsb=True.",
        ],
        "example": "set_preset_bank_select_and_program_change(preset='A', start_message_slot=0, bank_msb=0, program=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
    },
    "program_current_bank_from_json": {
        "group": "Bank Programming",
        "safety": "write",
        "verification": "live-verified",
        "transport": "mixed",
        "returns": "Writes the selected bank from a supported JSON spec and optionally verifies bank name plus preset A readback.",
        "notes": [
            "midi_channel is one-based here and converted internally before writing message payloads.",
            "verify=True performs follow-up probe reads against the device.",
        ],
        "example": 'program_current_bank_from_json(bank_json=\'{"bank_name":"AFX 001-008","presets":[]}\', save=False, output_port=\'Morningstar MC8 Pro 3\', input_port=\'Morningstar MC8 Pro 2\', midi_channel=1, verify=False)',
    },
    "safe_flash_bank": {
        "group": "Bank Programming",
        "safety": "write-flash",
        "verification": "live-verified",
        "transport": "editor-group-7",
        "returns": (
            "Guarded single-bank FLASH write: landmark-anchored navigation to the target bank, a "
            "pre-write bank-name assertion that aborts on mismatch, then the persistent group-7 upload."
        ),
        "notes": [
            "Preferred over raw upload_current_bank_from_json - prevents wrong-bank (off-by-one) corruption.",
            "expect_current_bank_name is REQUIRED and is the guard; a mismatch raises BankPositionError and writes nothing.",
            "anchor_bank_name must be a unique, correct bank name (e.g. the last programmed bank) at anchor_bank_number.",
            "dry_run=True rehearses navigation + guard without writing.",
            "After a real write the controller locks into editor-session mode: POWER-CYCLE before the next bank or verify. One bank per power-cycle.",
        ],
        "example": (
            "safe_flash_bank(bank_json='{\"bank_name\":\"AFX 001-008\",\"presets\":[]}', target_bank_number=1, "
            "expect_current_bank_name='AFX 009-016', anchor_bank_name='AFX 377-384', anchor_bank_number=48, dry_run=True)"
        ),
    },
    "build_current_bank_backup_json": {
        "group": "Offline Backup JSON",
        "safety": "offline-json",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Builds a draft current-bank backup container and returns it as a JSON string.",
        "notes": [
            "Does not talk to the controller.",
        ],
        "example": 'build_current_bank_backup_json(bank_json=\'{"bank_name":"AFX 001-008","presets":[]}\', pretty=True)',
    },
    "build_all_banks_backup_json": {
        "group": "Offline Backup JSON",
        "safety": "offline-json",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Builds a draft all-banks backup container with optional controllerData.",
        "notes": [
            "Does not talk to the controller.",
            "Accepts either bank specs or already wrapped bank backup objects.",
        ],
        "example": "build_all_banks_backup_json(banks_json='[]', controller_data_json='{}', pretty=True)",
    },
    "build_aux_controller_data_json": {
        "group": "Offline Backup JSON",
        "safety": "offline-json",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Builds a draft controllerData payload for controller-side aux mappings inferred from the editor backup path.",
        "notes": [
            "Does not talk to the controller.",
            "Entries using aux_switch are modeled as Omniport 1 resistor-ladder aux switches.",
            "TRS aux can also be modeled with omniport plus slot (tip, ring, tip+ring).",
            "The returned JSON is a draft reconstruction for backup generation, not a proven live restore payload.",
        ],
        "example": "build_aux_controller_data_json(aux_config_json='[{\"topology\":\"resistor_ladder_aux\",\"aux_switch\":1,\"kind\":\"fixed_function\",\"function\":\"bank_down\"}]', pretty=True)",
    },
    "build_trs_aux_fixed_functions_controller_data_json": {
        "group": "Offline Backup JSON",
        "safety": "offline-json",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Builds a draft controllerData payload for one Omniport configured as a TRS aux switch with fixed-function assignments on tip, ring, and/or tip+ring.",
        "notes": [
            "Does not talk to the controller.",
            "This is a typed wrapper over the generic aux controller-data builder.",
            "Useful for common bank-up and bank-down aux switch setups on Omniport 1.",
            "The returned JSON is a draft reconstruction for backup generation, not a proven live restore payload.",
        ],
        "example": "build_trs_aux_fixed_functions_controller_data_json(omniport=1, tip_function='bank_down', ring_function='bank_up', tip_ring_function='toggle_page', pretty=True)",
    },
    "inspect_backup_json": {
        "group": "Offline Backup JSON",
        "safety": "offline-json",
        "verification": "source-backed",
        "transport": "local-only",
        "returns": "Inspects a draft backup blob and returns a summary of banks, arrangements, and controllerData presence.",
        "notes": [
            "Does not talk to the controller.",
        ],
        "example": "inspect_backup_json(backup_json='{}')",
    },
}


def _list_outputs() -> list[str]:
    return list(mido.get_output_names())


def _list_inputs() -> list[str]:
    return list(mido.get_input_names())


def _looks_like_morningstar(name: str) -> bool:
    lowered = name.lower()
    return "morningstar" in lowered or "mc8" in lowered


def _candidate_ports(port_names: list[str]) -> list[str]:
    return [name for name in port_names if _looks_like_morningstar(name)]


def _resolve_port(name: str | None, available: list[str], env_name: str, kind: str) -> str:
    target = (name or "").strip()
    configured = (os.getenv(env_name, "") or "").strip()
    if not target and configured:
        target = configured

    if target:
        if target not in available:
            raise ValueError(f"{kind} port '{target}' not found. Use list_midi_ports.")
        return target

    candidates = _candidate_ports(available)
    if len(candidates) == 1:
        return candidates[0]

    if len(available) == 1:
        return available[0]

    if candidates:
        raise ValueError(
            f"Multiple candidate Morningstar {kind.lower()} ports found: {candidates}. "
            f"Set {env_name} or pass {kind.lower()}_port explicitly."
        )

    raise ValueError(
        f"No unique MIDI {kind.lower()} port. Set {env_name} or pass {kind.lower()}_port explicitly."
    )


def _resolve_out_port(name: str | None) -> str:
    return _resolve_port(name, _list_outputs(), "MORNINGSTAR_MC8_MIDI_OUT", "Output")


def _resolve_in_port(name: str | None) -> str:
    return _resolve_port(name, _list_inputs(), "MORNINGSTAR_MC8_MIDI_IN", "Input")


def _bytes_to_hex(values: list[int]) -> str:
    return " ".join(f"{value:02X}" for value in values)


def _checksum(values: list[int]) -> int:
    checksum = values[0]
    for value in values[1:-2]:
        checksum ^= value
    return checksum & 0x7F


def _build_request(
    op2: int,
    op3: int = 0,
    op4: int = 0,
    op5: int = 0,
    op6: int = 0,
    op7: int = 0,
    txn_id: int = 0,
    payload: list[int] | None = None,
    model_id: int = MC8_PRO_MODEL_ID,
) -> list[int]:
    if txn_id < 0 or txn_id > 127:
        raise ValueError("txn_id must be 0..127")

    frame = [
        0xF0,
        *MORNINGSTAR_MANUFACTURER_ID,
        model_id,
        0x00,
        MORNINGSTAR_OPCODE_1,
        op2 & 0x7F,
        op3 & 0x7F,
        op4 & 0x7F,
        op5 & 0x7F,
        op6 & 0x7F,
        op7 & 0x7F,
        txn_id,
        0x00,
        0x00,
    ]
    if payload:
        frame.extend(value & 0x7F for value in payload)
    frame.extend([0x00, 0xF7])
    frame[-2] = _checksum(frame)
    return frame


def _build_editor_sysex(
    function_1: int,
    function_2: int = 0,
    function_3: int = 0,
    function_4: int = 0,
    function_5: int = 0,
    function_6: int = 0,
    payload: list[int] | None = None,
    model_id: int = MC8_PRO_MODEL_ID,
) -> list[int]:
    frame = [
        0xF0,
        *MORNINGSTAR_MANUFACTURER_ID,
        model_id,
        0x00,
        function_1 & 0x7F,
        function_2 & 0x7F,
        function_3 & 0x7F,
        function_4 & 0x7F,
        function_5 & 0x7F,
        function_6 & 0x7F,
        0x00,
        0x00,
        0x00,
        0x00,
    ]
    if payload:
        frame.extend(value & 0x7F for value in payload)
    frame.extend([0x00, 0xF7])
    frame[-2] = _checksum(frame)
    return frame


def _is_morningstar_sysex(values: list[int]) -> bool:
    return (
        len(values) >= 18
        and values[0] == 0xF0
        and values[-1] == 0xF7
        and values[1:4] == MORNINGSTAR_MANUFACTURER_ID
        and values[6] == MORNINGSTAR_OPCODE_1
    )


def _is_morningstar_editor_sysex(values: list[int]) -> bool:
    return (
        len(values) >= 18
        and values[0] == 0xF0
        and values[-1] == 0xF7
        and values[1:4] == MORNINGSTAR_MANUFACTURER_ID
    )


def _validate_checksum(values: list[int]) -> bool:
    if len(values) < 18:
        return False
    return values[-2] == _checksum(values)


def _parse_response(values: list[int]) -> dict[str, Any]:
    if not _is_morningstar_sysex(values):
        raise ValueError("Not a Morningstar opcode-0x70 SysEx frame")

    parsed = {
        "hex": _bytes_to_hex(values),
        "model_id": values[4],
        "opcode_1": values[6],
        "opcode_2": values[7],
        "opcode_3": values[8],
        "opcode_4": values[9],
        "opcode_5": values[10],
        "opcode_6": values[11],
        "opcode_7": values[12],
        "transaction_id": values[13],
        "payload": values[16:-2],
        "checksum": values[-2],
        "checksum_valid": _validate_checksum(values),
    }

    if values[7] == 0x7F:
        ack_code = values[8]
        parsed["type"] = "ack"
        parsed["ack_code"] = ack_code
        parsed["ack_name"] = ACK_CODES.get(ack_code, f"UNKNOWN_{ack_code:02X}")
    else:
        parsed["type"] = "response"

    return parsed


def _parse_editor_sysex(values: list[int]) -> dict[str, Any]:
    if not _is_morningstar_editor_sysex(values):
        raise ValueError("Not a Morningstar editor-style SysEx frame")

    return {
        "hex": _bytes_to_hex(values),
        "model_id": values[4],
        "function_1": values[6],
        "function_2": values[7],
        "function_3": values[8],
        "function_4": values[9],
        "function_5": values[10],
        "function_6": values[11],
        "function_7": values[12],
        "function_8": values[13],
        "payload": values[16:-2],
        "checksum": values[-2],
        "checksum_valid": _validate_checksum(values),
    }


def _collect_matching_response(
    request: list[int],
    output_port: str,
    input_port: str,
    timeout_ms: int,
    txn_id: int,
) -> dict[str, Any]:
    collected: list[dict[str, Any]] = []
    deadline = time.time() + (timeout_ms / 1000.0)

    with mido.open_input(input_port) as in_port, mido.open_output(output_port) as out_port:
        out_port.send(mido.Message("sysex", data=request[1:-1]))

        while time.time() < deadline:
            for incoming in in_port.iter_pending():
                if incoming.type != "sysex":
                    collected.append({"type": incoming.type, "repr": str(incoming)})
                    continue

                full = [0xF0, *list(incoming.data), 0xF7]
                if not _is_morningstar_sysex(full):
                    collected.append({"type": "sysex", "hex": _bytes_to_hex(full), "matched": False})
                    continue

                parsed = _parse_response(full)
                parsed["matched"] = parsed["transaction_id"] == txn_id
                collected.append(parsed)
                if parsed["transaction_id"] == txn_id:
                    return {
                        "request_hex": _bytes_to_hex(request),
                        "response": parsed,
                        "received": collected,
                    }
            time.sleep(0.01)

    return {
        "request_hex": _bytes_to_hex(request),
        "response": None,
        "received": collected,
    }


def _ensure_success(response: dict[str, Any] | None) -> dict[str, Any]:
    if response is None:
        raise TimeoutError("No matching Morningstar SysEx response received before timeout")
    if response["type"] == "ack" and response.get("ack_code") != 0x00:
        raise RuntimeError(
            f"Morningstar returned {response.get('ack_name', 'UNKNOWN')} ({response.get('ack_code')})"
        )
    return response


def _decode_ascii_payload(payload: list[int]) -> str:
    return "".join(chr(value) for value in payload).rstrip()


def _encode_ascii_payload(text: str, size: int, label: str) -> list[int]:
    if size < 1:
        raise ValueError(f"{label} size must be positive")

    try:
        encoded = text.encode("ascii")
    except UnicodeEncodeError as ex:
        raise ValueError(f"{label} must contain ASCII characters only") from ex

    if len(encoded) > size:
        raise ValueError(f"{label} must be at most {size} ASCII characters")

    return list(encoded.ljust(size, b" "))


def _encode_ascii_message(text: str, size: int, label: str) -> list[int]:
    if size < 1:
        raise ValueError(f"{label} size must be positive")

    try:
        encoded = text.encode("ascii")
    except UnicodeEncodeError as ex:
        raise ValueError(f"{label} must contain ASCII characters only") from ex

    if len(encoded) > size:
        raise ValueError(f"{label} must be at most {size} ASCII characters")

    return list(encoded)


def _parse_preset_id(preset: str) -> int:
    text = preset.strip().upper()
    if not text:
        raise ValueError("preset cannot be empty")
    if len(text) == 1 and "A" <= text <= "Z":
        return ord(text) - ord("A")
    value = int(text, 10)
    if value < 0 or value > 31:
        raise ValueError("preset must be A-Z or a number in 0..31")
    return value


def _validate_7bit_value(value: int, label: str) -> int:
    if value < 0 or value > 127:
        raise ValueError(f"{label} must be in 0..127")
    return value


def _parse_message_slot(slot: int) -> int:
    if slot < 0 or slot > 15:
        raise ValueError("message_slot must be in 0..15")
    return slot


def _parse_json_argument(text: str, label: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as ex:
        raise ValueError(f"{label} must be valid JSON") from ex


def _parse_int(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as ex:
        raise ValueError(f"{label} must be an integer") from ex


def _validate_raw_payload(payload: list[int]) -> list[int]:
    if len(payload) > MAX_RAW_MESSAGE_PAYLOAD_SIZE:
        raise ValueError(
            f"payload must have at most {MAX_RAW_MESSAGE_PAYLOAD_SIZE} 7-bit values"
        )
    return [_validate_7bit_value(value, "payload value") for value in payload]


def _preset_label_from_number(preset_number: int) -> str:
    if preset_number < 0:
        raise ValueError("preset_number must be non-negative")
    if preset_number >= MC8_PRO_PRESET_COUNT:
        return f"slot_{preset_number}"
    return chr(ord("A") + preset_number)


def _editor_preset_label_from_number(preset_number: int) -> str:
    if preset_number < 0:
        raise ValueError("preset_number must be non-negative")
    if preset_number >= MC8_PRO_EDITOR_UPLOAD_PRESET_COUNT:
        return f"slot_{preset_number}"
    page_size = 8
    page_number, slot_number = divmod(preset_number, page_size)
    return f"{chr(ord('A') + slot_number)}{page_number + 1}"


def _preset_number_from_label(preset: str) -> int:
    value = _parse_preset_id(preset)
    if value >= MC8_PRO_PRESET_COUNT:
        raise ValueError(f"preset must resolve to 0..{MC8_PRO_PRESET_COUNT - 1} for MC8 Pro")
    return value


def _build_pc_message_payload(
    program: int,
    midi_channel: int,
    action_type: int,
    toggle_type: int,
) -> list[int]:
    return [
        _validate_7bit_value(action_type, "action_type"),
        _validate_7bit_value(toggle_type, "toggle_type"),
        _validate_7bit_value(program, "program"),
        _validate_7bit_value(midi_channel, "midi_channel"),
    ]


def _build_cc_message_payload(
    cc_number: int,
    cc_value: int,
    midi_channel: int,
    action_type: int,
    toggle_type: int,
) -> list[int]:
    return [
        _validate_7bit_value(action_type, "action_type"),
        _validate_7bit_value(toggle_type, "toggle_type"),
        _validate_7bit_value(cc_number, "cc_number"),
        _validate_7bit_value(cc_value, "cc_value"),
        _validate_7bit_value(midi_channel, "midi_channel"),
    ]


def _build_note_message_payload(
    note_number: int,
    velocity: int,
    midi_channel: int,
    action_type: int,
    toggle_type: int,
) -> list[int]:
    return [
        _validate_7bit_value(action_type, "action_type"),
        _validate_7bit_value(toggle_type, "toggle_type"),
        _validate_7bit_value(note_number, "note_number"),
        _validate_7bit_value(velocity, "velocity"),
        _validate_7bit_value(midi_channel, "midi_channel"),
    ]


def _run_probe(
    op2: int,
    op3: int = 0,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 1,
) -> dict[str, Any]:
    if timeout_ms < 1 or timeout_ms > 10000:
        raise ValueError("timeout_ms must be 1..10000")

    request = _build_request(op2=op2, op3=op3, txn_id=txn_id)
    out_name = _resolve_out_port(output_port)
    in_name = _resolve_in_port(input_port)
    result = _collect_matching_response(request, out_name, in_name, timeout_ms, txn_id)

    return {
        "status": "completed" if result["response"] else "timeout",
        "out_port": out_name,
        "in_port": in_name,
        "timeout_ms": timeout_ms,
        **result,
    }


def _run_write(
    op2: int,
    payload: list[int],
    op3: int = 0,
    op4: int = 0,
    op5: int = 0,
    op6: int = 0,
    op7: int = 0,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 1,
) -> dict[str, Any]:
    if timeout_ms < 1 or timeout_ms > 10000:
        raise ValueError("timeout_ms must be 1..10000")

    request = _build_request(
        op2=op2,
        op3=op3,
        op4=op4,
        op5=op5,
        op6=op6,
        op7=op7,
        txn_id=txn_id,
        payload=payload,
    )
    out_name = _resolve_out_port(output_port)
    in_name = _resolve_in_port(input_port)
    result = _collect_matching_response(request, out_name, in_name, timeout_ms, txn_id)
    response = _ensure_success(result["response"])

    return {
        "status": "completed",
        "out_port": out_name,
        "in_port": in_name,
        "timeout_ms": timeout_ms,
        **result,
        "response": response,
    }


def _send_write_without_response(
    op2: int,
    payload: list[int],
    op3: int = 0,
    op4: int = 0,
    op5: int = 0,
    op6: int = 0,
    op7: int = 0,
    output_port: str = "",
    txn_id: int = 0,
) -> dict[str, Any]:
    request = _build_request(
        op2=op2,
        op3=op3,
        op4=op4,
        op5=op5,
        op6=op6,
        op7=op7,
        txn_id=txn_id,
        payload=payload,
    )
    out_name = _resolve_out_port(output_port)
    with mido.open_output(out_name) as out_port:
        out_port.send(mido.Message("sysex", data=request[1:-1]))

    return {
        "status": "sent",
        "out_port": out_name,
        "request_hex": _bytes_to_hex(request),
        "response": None,
        "received": [],
    }


def _send_function_without_response(
    op2: int,
    op3: int = 0,
    op4: int = 0,
    op5: int = 0,
    op6: int = 0,
    op7: int = 0,
    output_port: str = "",
    txn_id: int = 0,
) -> dict[str, Any]:
    request = _build_request(
        op2=op2,
        op3=op3,
        op4=op4,
        op5=op5,
        op6=op6,
        op7=op7,
        txn_id=txn_id,
    )
    out_name = _resolve_out_port(output_port)
    with mido.open_output(out_name) as out_port:
        out_port.send(mido.Message("sysex", data=request[1:-1]))

    return {
        "status": "sent",
        "out_port": out_name,
        "request_hex": _bytes_to_hex(request),
        "response": None,
        "received": [],
    }


def _save_opcode(save: bool) -> int:
    return 0x7F if save else 0x00


def _send_controller_function(
    function_id: int,
    value: int = 0,
    output_port: str = "",
    txn_id: int = 0,
) -> dict[str, Any]:
    return _send_write_without_response(
        op2=0x00,
        op3=_validate_7bit_value(function_id, "function_id"),
        payload=[_validate_7bit_value(value, "value")],
        output_port=output_port,
        txn_id=txn_id,
    )


def _write_preset_name(
    op2: int,
    preset: str,
    value: str,
    size: int,
    decoded_key: str,
    output_port: str,
    input_port: str,
    timeout_ms: int,
    txn_id: int,
    save: bool,
) -> dict[str, Any]:
    preset_number = _parse_preset_id(preset)
    payload = _encode_ascii_payload(value, size=size, label=decoded_key)
    result = _run_write(
        op2=op2,
        op3=preset_number,
        op6=_save_opcode(save),
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "preset": preset,
        "preset_number": preset_number,
        decoded_key: value,
        "saved": save,
    }
    return result


def _write_preset_message(
    preset: str,
    message_slot: int,
    message_type: int,
    payload: list[int],
    output_port: str,
    input_port: str,
    timeout_ms: int,
    txn_id: int,
    save: bool,
) -> dict[str, Any]:
    preset_number = _parse_preset_id(preset)
    slot_number = _parse_message_slot(message_slot)
    result = _run_write(
        op2=0x04,
        op3=preset_number,
        op4=slot_number,
        op5=message_type,
        op6=_save_opcode(save),
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "preset": preset,
        "preset_number": preset_number,
        "message_slot": slot_number,
        "message_type": message_type,
        "payload": payload,
        "saved": save,
    }
    return result


def _parse_raw_payload_json(payload_json: str) -> list[int]:
    payload = _parse_json_argument(payload_json, "payload_json")
    if not isinstance(payload, list):
        raise ValueError("payload_json must decode to a JSON array of 7-bit integers")
    return _validate_raw_payload([_parse_int(value, "payload value") for value in payload])


def _write_controller_settings_section_raw(
    payload_json: str,
    section_name: str,
    op3: int,
    output_port: str,
    input_port: str,
    timeout_ms: int,
    txn_id: int,
    op4: int = 0,
    op5: int = 0,
) -> dict[str, Any]:
    payload = _parse_raw_payload_json(payload_json)
    result = _run_write(
        op2=CONTROLLER_SETTINGS_WRITE_OPCODE_2,
        op3=op3,
        op4=op4,
        op5=op5,
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "section": section_name,
        "payload": payload,
    }
    return result


def _normalize_supported_bank_spec(raw_spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_spec, dict):
        raise ValueError("bank spec must be a JSON object")

    if isinstance(raw_spec.get("bankData"), dict) and isinstance(raw_spec["bankData"].get("bank"), dict):
        raw_spec = raw_spec["bankData"]["bank"]

    if "bankName" in raw_spec and "presetArray" in raw_spec:
        return _normalize_backup_bank_spec(raw_spec)

    if "presets" in raw_spec:
        return _normalize_program_bank_spec(raw_spec)

    if "page_1" in raw_spec or "page_2" in raw_spec:
        return _normalize_layout_bank_spec(raw_spec)

    raise ValueError(
        "Unsupported bank JSON shape. Expected a supported program spec, layout spec, or bankData.bank backup object."
    )


def _normalize_program_bank_spec(raw_spec: dict[str, Any]) -> dict[str, Any]:
    bank_name = str(raw_spec.get("bank_name") or raw_spec.get("bankName") or "").strip()
    if not bank_name:
        raise ValueError("bank_name is required")

    raw_presets = raw_spec.get("presets")
    if not isinstance(raw_presets, list):
        raise ValueError("presets must be a JSON array")

    presets: list[dict[str, Any]] = []
    seen_presets: set[int] = set()
    for index, preset_spec in enumerate(raw_presets):
        if not isinstance(preset_spec, dict):
            raise ValueError(f"presets[{index}] must be an object")

        preset_number = _preset_number_from_label(str(preset_spec.get("preset") or ""))
        if preset_number in seen_presets:
            raise ValueError(f"Duplicate preset entry for {_preset_label_from_number(preset_number)}")
        seen_presets.add(preset_number)

        messages = preset_spec.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError(f"presets[{index}].messages must be an array")

        normalized_messages: list[dict[str, Any]] = []
        for message_index, message_spec in enumerate(messages):
            if not isinstance(message_spec, dict):
                raise ValueError(
                    f"presets[{index}].messages[{message_index}] must be an object"
                )
            normalized_messages.append(_normalize_program_message_spec(message_spec))

        presets.append(
            {
                "preset": _preset_label_from_number(preset_number),
                "preset_number": preset_number,
                "short_name": str(preset_spec.get("short_name") or preset_spec.get("shortName") or ""),
                "toggle_name": str(
                    preset_spec.get("toggle_name") or preset_spec.get("toggleName") or ""
                ),
                "long_name": str(preset_spec.get("long_name") or preset_spec.get("longName") or ""),
                "messages": normalized_messages,
                "to_toggle": _parse_int(preset_spec.get("to_toggle", preset_spec.get("toToggle", 0)), "to_toggle"),
                "to_blink": _parse_int(preset_spec.get("to_blink", preset_spec.get("toBlink", 0)), "to_blink"),
                "toggle_group": _parse_int(
                    preset_spec.get("toggle_group", preset_spec.get("toggleGroup", 0)),
                    "toggle_group",
                ),
                "name_color": _parse_int(preset_spec.get("name_color", preset_spec.get("nameColor", 0)), "name_color"),
                "background_color": _parse_int(
                    preset_spec.get("background_color", preset_spec.get("backgroundColor", 0)),
                    "background_color",
                ),
                "led_color": _parse_int(preset_spec.get("led_color", preset_spec.get("ledColor", 0)), "led_color"),
            }
        )

    presets.sort(key=lambda item: item["preset_number"])
    return {
        "bank_name": bank_name,
        "presets": presets,
    }


def _normalize_program_message_spec(raw_message: dict[str, Any]) -> dict[str, Any]:
    kind = str(raw_message.get("kind") or "").strip().lower()
    if not kind:
        raise ValueError("message kind is required")

    if kind == "pc":
        return {
            "kind": "pc",
            "message_slot": _parse_message_slot(_parse_int(raw_message.get("message_slot", 0), "message_slot")),
            "program": _validate_7bit_value(_parse_int(raw_message.get("program", 0), "program"), "program"),
            "midi_channel": _validate_7bit_value(
                _parse_int(raw_message.get("midi_channel", 0), "midi_channel"),
                "midi_channel",
            ),
            "action_type": _validate_7bit_value(
                _parse_int(raw_message.get("action_type", ACTION_TYPE_PRESS), "action_type"),
                "action_type",
            ),
            "toggle_type": _validate_7bit_value(
                _parse_int(raw_message.get("toggle_type", TOGGLE_TYPE_POS_1), "toggle_type"),
                "toggle_type",
            ),
        }

    if kind == "cc":
        return {
            "kind": "cc",
            "message_slot": _parse_message_slot(_parse_int(raw_message.get("message_slot", 0), "message_slot")),
            "cc_number": _validate_7bit_value(
                _parse_int(raw_message.get("cc_number", 0), "cc_number"),
                "cc_number",
            ),
            "cc_value": _validate_7bit_value(
                _parse_int(raw_message.get("cc_value", 0), "cc_value"),
                "cc_value",
            ),
            "midi_channel": _validate_7bit_value(
                _parse_int(raw_message.get("midi_channel", 0), "midi_channel"),
                "midi_channel",
            ),
            "action_type": _validate_7bit_value(
                _parse_int(raw_message.get("action_type", ACTION_TYPE_PRESS), "action_type"),
                "action_type",
            ),
            "toggle_type": _validate_7bit_value(
                _parse_int(raw_message.get("toggle_type", TOGGLE_TYPE_POS_1), "toggle_type"),
                "toggle_type",
            ),
        }

    if kind == "bank_select_pc":
        return {
            "kind": "bank_select_pc",
            "start_message_slot": _parse_message_slot(
                _parse_int(raw_message.get("start_message_slot", 0), "start_message_slot")
            ),
            "bank_msb": _validate_7bit_value(
                _parse_int(raw_message.get("bank_msb", 0), "bank_msb"),
                "bank_msb",
            ),
            "include_bank_lsb": bool(raw_message.get("include_bank_lsb", False)),
            "bank_lsb": _validate_7bit_value(
                _parse_int(raw_message.get("bank_lsb", 0), "bank_lsb"),
                "bank_lsb",
            ),
            "program": _validate_7bit_value(_parse_int(raw_message.get("program", 0), "program"), "program"),
            "midi_channel": _validate_7bit_value(
                _parse_int(raw_message.get("midi_channel", 0), "midi_channel"),
                "midi_channel",
            ),
            "action_type": _validate_7bit_value(
                _parse_int(raw_message.get("action_type", ACTION_TYPE_PRESS), "action_type"),
                "action_type",
            ),
            "toggle_type": _validate_7bit_value(
                _parse_int(raw_message.get("toggle_type", TOGGLE_TYPE_POS_1), "toggle_type"),
                "toggle_type",
            ),
        }

    if kind == "raw":
        payload = raw_message.get("payload")
        if not isinstance(payload, list):
            raise ValueError("raw message payload must be an array")
        return {
            "kind": "raw",
            "message_slot": _parse_message_slot(_parse_int(raw_message.get("message_slot", 0), "message_slot")),
            "message_type": _validate_7bit_value(
                _parse_int(raw_message.get("message_type", 0), "message_type"),
                "message_type",
            ),
            "payload": _validate_raw_payload([_parse_int(value, "payload value") for value in payload]),
        }

    raise ValueError(f"Unsupported message kind '{kind}'")


def _normalize_layout_bank_spec(raw_spec: dict[str, Any]) -> dict[str, Any]:
    bank_name = str(raw_spec.get("bank_name") or raw_spec.get("bankName") or "").strip()
    if not bank_name:
        raise ValueError("layout bank spec requires bank_name")

    presets_by_number: dict[int, dict[str, Any]] = {}
    for key in ("page_1", "page_2"):
        page_entries = raw_spec.get(key, [])
        if not isinstance(page_entries, list):
            raise ValueError(f"{key} must be an array")
        for index, entry in enumerate(page_entries):
            if not isinstance(entry, dict):
                raise ValueError(f"{key}[{index}] must be an object")
            preset_number = _preset_number_from_label(str(entry.get("mc8_preset") or ""))
            preset_entry = presets_by_number.setdefault(
                preset_number,
                {
                    "preset": _preset_label_from_number(preset_number),
                    "preset_number": preset_number,
                    "short_name": "",
                    "toggle_name": "",
                    "long_name": "",
                    "messages": [],
                    "to_toggle": 0,
                    "to_blink": 0,
                    "toggle_group": 0,
                    "name_color": 0,
                    "background_color": 0,
                    "led_color": 0,
                },
            )
            preset_entry["short_name"] = str(entry.get("short_name") or preset_entry["short_name"])
            preset_entry["long_name"] = str(entry.get("long_name") or preset_entry["long_name"])

            if "cc0" in entry and "pc" in entry:
                preset_entry["messages"].append(
                    {
                        "kind": "bank_select_pc",
                        "start_message_slot": 0,
                        "bank_msb": _validate_7bit_value(_parse_int(entry["cc0"], "cc0"), "cc0"),
                        "include_bank_lsb": False,
                        "bank_lsb": 0,
                        "program": _validate_7bit_value(_parse_int(entry["pc"], "pc"), "pc"),
                        "midi_channel": 0,
                        "action_type": ACTION_TYPE_PRESS,
                        "toggle_type": TOGGLE_TYPE_POS_1,
                    }
                )
            elif "cc_number" in entry and "cc_value" in entry:
                preset_entry["messages"].append(
                    {
                        "kind": "cc",
                        "message_slot": 0,
                        "cc_number": _validate_7bit_value(
                            _parse_int(entry["cc_number"], "cc_number"),
                            "cc_number",
                        ),
                        "cc_value": _validate_7bit_value(
                            _parse_int(entry["cc_value"], "cc_value"),
                            "cc_value",
                        ),
                        "midi_channel": 0,
                        "action_type": ACTION_TYPE_PRESS,
                        "toggle_type": TOGGLE_TYPE_POS_1,
                    }
                )

    return {
        "bank_name": bank_name,
        "presets": [presets_by_number[number] for number in sorted(presets_by_number)],
    }


def _normalize_backup_bank_spec(raw_bank: dict[str, Any]) -> dict[str, Any]:
    presets_by_number: dict[int, dict[str, Any]] = {}
    for index, preset in enumerate(raw_bank.get("presetArray", [])):
        if not isinstance(preset, dict):
            raise ValueError(f"presetArray[{index}] must be an object")
        preset_number = _parse_int(preset.get("presetNum", index), "presetNum")
        messages: list[dict[str, Any]] = []
        for message_index, message in enumerate(preset.get("msgArray", [])):
            if not isinstance(message, dict):
                raise ValueError(
                    f"presetArray[{index}].msgArray[{message_index}] must be an object"
                )
            normalized = _normalize_backup_message_to_program_message(message)
            if normalized is not None:
                messages.append(normalized)

        presets_by_number[preset_number] = {
            "preset": _editor_preset_label_from_number(preset_number),
            "preset_number": preset_number,
            "short_name": str(preset.get("shortName") or ""),
            "toggle_name": str(preset.get("toggleName") or ""),
            "long_name": str(preset.get("longName") or ""),
            "messages": sorted(
                messages,
                key=lambda item: item.get("start_message_slot", item.get("message_slot", 0)),
            ),
            "to_toggle": _parse_int(preset.get("toToggle", 0), "toToggle"),
            "to_blink": _parse_int(preset.get("toBlink", 0), "toBlink"),
            "toggle_group": _parse_int(preset.get("toggleGroup", 0), "toggleGroup"),
            "name_color": _parse_int(preset.get("nameColor", 0), "nameColor"),
            "background_color": _parse_int(preset.get("backgroundColor", 0), "backgroundColor"),
            "led_color": _parse_int(preset.get("ledColor", 0), "ledColor"),
        }

    return {
        "bank_name": str(raw_bank.get("bankName") or "").strip(),
        "presets": [presets_by_number[number] for number in sorted(presets_by_number)],
    }


def _normalize_backup_message_to_program_message(message: dict[str, Any]) -> dict[str, Any] | None:
    message_type = _parse_int(message.get("type", 0), "type")
    message_slot = _parse_message_slot(_parse_int(message.get("messageNumber", 0), "messageNumber"))
    action_type = _validate_7bit_value(_parse_int(message.get("action", 0), "action"), "action")
    toggle_type = _validate_7bit_value(_parse_int(message.get("toggle", 0), "toggle"), "toggle")
    midi_channel = _validate_7bit_value(_parse_int(message.get("channel", 0), "channel"), "channel")

    if message_type == MESSAGE_TYPE_PC:
        return {
            "kind": "pc",
            "message_slot": message_slot,
            "program": _validate_7bit_value(_parse_int(message.get("data1", 0), "data1"), "data1"),
            "midi_channel": midi_channel,
            "action_type": action_type,
            "toggle_type": toggle_type,
        }

    if message_type == MESSAGE_TYPE_CC:
        return {
            "kind": "cc",
            "message_slot": message_slot,
            "cc_number": _validate_7bit_value(_parse_int(message.get("data1", 0), "data1"), "data1"),
            "cc_value": _validate_7bit_value(_parse_int(message.get("data2", 0), "data2"), "data2"),
            "midi_channel": midi_channel,
            "action_type": action_type,
            "toggle_type": toggle_type,
        }

    return None


def _program_current_bank_from_spec(
    bank_spec: dict[str, Any],
    output_port: str,
    input_port: str,
    save: bool,
    default_midi_channel: int,
) -> list[dict[str, Any]]:
    writes: list[dict[str, Any]] = []
    writes.append(
        set_current_bank_name(
            bank_name=bank_spec["bank_name"],
            save=save,
            output_port=output_port,
            input_port=input_port,
        )
    )

    for preset_spec in bank_spec["presets"]:
        preset = preset_spec["preset"]
        for message_spec in preset_spec["messages"]:
            kind = message_spec["kind"]
            if kind == "pc":
                writes.append(
                    set_preset_message_pc(
                        preset=preset,
                        message_slot=message_spec["message_slot"],
                        program=message_spec["program"],
                        midi_channel=message_spec.get("midi_channel", default_midi_channel),
                        save=save,
                        action_type=message_spec["action_type"],
                        toggle_type=message_spec["toggle_type"],
                        output_port=output_port,
                        input_port=input_port,
                    )
                )
            elif kind == "cc":
                writes.append(
                    set_preset_message_cc(
                        preset=preset,
                        message_slot=message_spec["message_slot"],
                        cc_number=message_spec["cc_number"],
                        cc_value=message_spec["cc_value"],
                        midi_channel=message_spec.get("midi_channel", default_midi_channel),
                        save=save,
                        action_type=message_spec["action_type"],
                        toggle_type=message_spec["toggle_type"],
                        output_port=output_port,
                        input_port=input_port,
                    )
                )
            elif kind == "bank_select_pc":
                writes.append(
                    set_preset_bank_select_and_program_change(
                        preset=preset,
                        start_message_slot=message_spec["start_message_slot"],
                        bank_msb=message_spec["bank_msb"],
                        program=message_spec["program"],
                        midi_channel=message_spec.get("midi_channel", default_midi_channel),
                        save=save,
                        include_bank_lsb=message_spec["include_bank_lsb"],
                        bank_lsb=message_spec["bank_lsb"],
                        action_type=message_spec["action_type"],
                        toggle_type=message_spec["toggle_type"],
                        output_port=output_port,
                        input_port=input_port,
                    )
                )
            elif kind == "raw":
                writes.append(
                    set_preset_message_raw(
                        preset=preset,
                        message_slot=message_spec["message_slot"],
                        message_type=message_spec["message_type"],
                        payload_json=json.dumps(message_spec["payload"]),
                        save=save,
                        output_port=output_port,
                        input_port=input_port,
                    )
                )
        short_name = preset_spec.get("short_name", "")
        toggle_name = preset_spec.get("toggle_name", "")
        long_name = preset_spec.get("long_name", "")
        if short_name:
            writes.append(
                set_preset_short_name(
                    preset=preset,
                    short_name=short_name,
                    save=save,
                    output_port=output_port,
                    input_port=input_port,
                )
            )
        if toggle_name:
            writes.append(
                set_preset_toggle_name(
                    preset=preset,
                    toggle_name=toggle_name,
                    save=save,
                    output_port=output_port,
                    input_port=input_port,
                )
            )
        if long_name:
            writes.append(
                set_preset_long_name(
                    preset=preset,
                    long_name=long_name,
                    save=save,
                    output_port=output_port,
                    input_port=input_port,
                )
            )

    return writes



def _build_backup_message_json(message_number: int, message_spec: dict[str, Any]) -> dict[str, Any]:
    data_fields = {f"data{index}": 0 for index in range(1, MESSAGE_JSON_DATA_FIELD_COUNT + 1)}
    message_type = 0
    channel = 0
    action_type = 0
    toggle_type = 0

    if message_spec["kind"] == "pc":
        message_type = MESSAGE_TYPE_PC
        data_fields["data1"] = message_spec["program"]
        channel = message_spec["midi_channel"]
        action_type = message_spec["action_type"]
        toggle_type = message_spec["toggle_type"]
    elif message_spec["kind"] == "cc":
        message_type = MESSAGE_TYPE_CC
        data_fields["data1"] = message_spec["cc_number"]
        data_fields["data2"] = message_spec["cc_value"]
        channel = message_spec["midi_channel"]
        action_type = message_spec["action_type"]
        toggle_type = message_spec["toggle_type"]
    else:
        raise ValueError(
            "Backup JSON generation currently supports only pc, cc, and bank_select_pc message kinds"
        )

    return {
        "messageNumber": message_number,
        **data_fields,
        "channel": channel,
        "type": message_type,
        "action": action_type,
        "toggle": toggle_type,
        "modelName": "",
        "brandName": "",
        "isFromMidiDictionary": False,
        "isFromUserLibrary": False,
        "msgInfo": "",
    }


def _build_backup_preset_json(preset_number: int, bank_number: int, preset_spec: dict[str, Any]) -> dict[str, Any]:
    msg_array: list[dict[str, Any]] = []
    for message_spec in preset_spec["messages"]:
        if message_spec["kind"] == "bank_select_pc":
            slot = message_spec["start_message_slot"]
            msg_array.append(
                _build_backup_message_json(
                    slot,
                    {
                        "kind": "cc",
                        "cc_number": 0,
                        "cc_value": message_spec["bank_msb"],
                        "midi_channel": message_spec["midi_channel"],
                        "action_type": message_spec["action_type"],
                        "toggle_type": message_spec["toggle_type"],
                    },
                )
            )
            slot += 1
            if message_spec["include_bank_lsb"]:
                msg_array.append(
                    _build_backup_message_json(
                        slot,
                        {
                            "kind": "cc",
                            "cc_number": 32,
                            "cc_value": message_spec["bank_lsb"],
                            "midi_channel": message_spec["midi_channel"],
                            "action_type": message_spec["action_type"],
                            "toggle_type": message_spec["toggle_type"],
                        },
                    )
                )
                slot += 1
            msg_array.append(
                _build_backup_message_json(
                    slot,
                    {
                        "kind": "pc",
                        "program": message_spec["program"],
                        "midi_channel": message_spec["midi_channel"],
                        "action_type": message_spec["action_type"],
                        "toggle_type": message_spec["toggle_type"],
                    },
                )
            )
        else:
            msg_array.append(
                _build_backup_message_json(
                    message_spec["message_slot"],
                    message_spec,
                )
            )

    return {
        "presetNum": preset_number,
        "bankNum": bank_number,
        "isExp": False,
        "shortName": preset_spec.get("short_name", ""),
        "toggleName": preset_spec.get("toggle_name", ""),
        "longName": preset_spec.get("long_name", ""),
        "shiftName": "",
        "toToggle": preset_spec.get("to_toggle", 0),
        "toBlink": preset_spec.get("to_blink", 0),
        "toMsgScroll": 0,
        "toggleGroup": preset_spec.get("toggle_group", 0),
        "ledColor": preset_spec.get("led_color", 0),
        "ledToggleColor": 0,
        "ledShiftColor": 0,
        "nameColor": preset_spec.get("name_color", 0),
        "nameToggleColor": 0,
        "nameShiftColor": 0,
        "backgroundColor": preset_spec.get("background_color", 0),
        "toggleBackgroundColor": 0,
        "shiftBackgroundColor": 0,
        "msgArray": sorted(msg_array, key=lambda item: item["messageNumber"]),
    }


def _build_current_bank_backup_data(
    bank_spec: dict[str, Any],
    bank_number: int,
    profile_number: int,
    model_id: int,
) -> dict[str, Any]:
    preset_lookup = {preset["preset_number"]: preset for preset in bank_spec["presets"]}
    preset_array = []
    for preset_number in range(MC8_PRO_EDITOR_UPLOAD_PRESET_COUNT):
        preset_spec = preset_lookup.get(
            preset_number,
            {
                "preset": _editor_preset_label_from_number(preset_number),
                "preset_number": preset_number,
                "short_name": "",
                "toggle_name": "",
                "long_name": "",
                "messages": [],
                "to_toggle": 0,
                "to_blink": 0,
                "toggle_group": 0,
                "name_color": 0,
                "background_color": 0,
                "led_color": 0,
            },
        )
        preset_array.append(_build_backup_preset_json(preset_number, bank_number, preset_spec))

    bank = {
        "bankName": bank_spec["bank_name"],
        "bankDescription": "",
        "toDisplayDescription": False,
        "bankClearToggle": False,
        "pageLimit": 0,
        "bankNameLength": MC8_PRO_BANK_NAME_SIZE,
        "profileNumber": profile_number,
        "bankNumber": bank_number,
        "modelID": model_id,
        "isColorEnabled": True,
        "backgroundColor": 0,
        "textColor": 0,
        "midiMsgArray": [],
        "presetArray": preset_array,
        "expPresetArray": [],
    }
    return {
        "bankData": {
            "bank": bank,
            "bankArrangement": {
                "type": "bank_arrangement",
                "data": {
                    "bankNum": bank_number,
                    "bankName": bank_spec["bank_name"],
                    "bankNameLength": MC8_PRO_BANK_NAME_SIZE,
                },
            },
        }
    }


def _editor_default_preset_spec(preset_number: int) -> dict[str, Any]:
    preset_label = _editor_preset_label_from_number(preset_number)
    return {
        "preset": preset_label,
        "preset_number": preset_number,
        "short_name": "",
        "toggle_name": "",
        "long_name": "",
        "shift_name": "",
        "messages": [],
        "to_toggle": 0,
        "to_blink": 0,
        "to_msg_scroll": 0,
        "toggle_group": 0,
        "name_color": 0,
        "toggle_name_color": 0,
        "shift_name_color": 0,
        "background_color": 0,
        "toggle_background_color": 0,
        "shift_background_color": 0,
        "led_color": 0,
        "toggle_led_color": 0,
        "shift_led_color": 0,
    }


def _editor_blank_name_payload(size: int) -> list[int]:
    return _encode_ascii_payload("", size=size, label="editor_name")


def _editor_empty_message_bytes(message_number: int) -> list[int]:
    return [
        message_number,
        0,
        0,
        0,
        0,
        1,
        0,
        2,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]


def _editor_message_bytes_for_kind(message_number: int, message_spec: dict[str, Any]) -> list[int]:
    kind = message_spec["kind"]
    # MC8 stores the message MIDI channel 1-based (channel 1 -> byte 1); specs use 0-based.
    channel_byte = _validate_7bit_value(message_spec["midi_channel"] + 1, "midi_channel")
    if kind == "pc":
        data_fields = [message_spec["program"], 0, 0] + [0] * 15
        return [
            message_number,
            MESSAGE_TYPE_PC,
            *data_fields[:3],
            channel_byte,
            message_spec["action_type"],
            message_spec["toggle_type"],
            *data_fields[3:],
        ]

    if kind == "cc":
        data_fields = [message_spec["cc_number"], message_spec["cc_value"], 0] + [0] * 15
        return [
            message_number,
            MESSAGE_TYPE_CC,
            *data_fields[:3],
            channel_byte,
            message_spec["action_type"],
            message_spec["toggle_type"],
            *data_fields[3:],
        ]

    raise ValueError(f"Editor upload does not support message kind '{kind}'")


def _editor_message_slot_map(preset_spec: dict[str, Any]) -> dict[int, list[int]]:
    slot_map: dict[int, list[int]] = {}
    for message_spec in preset_spec["messages"]:
        kind = message_spec["kind"]
        if kind in {"pc", "cc"}:
            slot_map[message_spec["message_slot"]] = _editor_message_bytes_for_kind(
                message_spec["message_slot"],
                message_spec,
            )
            continue

        if kind == "bank_select_pc":
            slot_number = message_spec["start_message_slot"]
            slot_map[slot_number] = _editor_message_bytes_for_kind(
                slot_number,
                {
                    "kind": "cc",
                    "cc_number": 0,
                    "cc_value": message_spec["bank_msb"],
                    "midi_channel": message_spec["midi_channel"],
                    "action_type": message_spec["action_type"],
                    "toggle_type": message_spec["toggle_type"],
                },
            )
            slot_number += 1
            if message_spec["include_bank_lsb"]:
                slot_map[slot_number] = _editor_message_bytes_for_kind(
                    slot_number,
                    {
                        "kind": "cc",
                        "cc_number": 32,
                        "cc_value": message_spec["bank_lsb"],
                        "midi_channel": message_spec["midi_channel"],
                        "action_type": message_spec["action_type"],
                        "toggle_type": message_spec["toggle_type"],
                    },
                )
                slot_number += 1
            slot_map[slot_number] = _editor_message_bytes_for_kind(
                slot_number,
                {
                    "kind": "pc",
                    "program": message_spec["program"],
                    "midi_channel": message_spec["midi_channel"],
                    "action_type": message_spec["action_type"],
                    "toggle_type": message_spec["toggle_type"],
                },
            )
            continue

        raise ValueError(f"Editor upload does not support message kind '{kind}'")

    return slot_map


def _encode_editor_preset_chunk(
    preset_spec: dict[str, Any],
    bank_number: int,
    is_exp: bool = False,
) -> list[int]:
    payload = [
        0x7F,
        0x00,
        0x03,
        _validate_7bit_value(bank_number + 1, "bank_number"),  # preset header bank number is 1-based
        _validate_7bit_value(preset_spec["preset_number"], "preset_number"),
        1 if is_exp else 0,
    ]
    slot_map = _editor_message_slot_map(preset_spec)
    for message_number in range(MC8_PRO_PRESET_MESSAGE_COUNT):
        payload.extend([0x7F, 0x01, 23])
        payload.extend(slot_map.get(message_number, _editor_empty_message_bytes(message_number)))

    payload.extend([0x7F, 0x02, MC8_PRO_SHORT_NAME_SIZE])
    payload.extend(_encode_ascii_payload(preset_spec.get("short_name", ""), MC8_PRO_SHORT_NAME_SIZE, "short_name"))
    payload.extend([0x7F, 0x03, MC8_PRO_TOGGLE_NAME_SIZE])
    payload.extend(_encode_ascii_payload(preset_spec.get("toggle_name", ""), MC8_PRO_TOGGLE_NAME_SIZE, "toggle_name"))
    payload.extend([0x7F, 0x04, MC8_PRO_LONG_NAME_SIZE])
    payload.extend(_encode_ascii_payload(preset_spec.get("long_name", ""), MC8_PRO_LONG_NAME_SIZE, "long_name"))
    payload.extend(
        [
            0x7F,
            0x05,
            32,
            preset_spec.get("to_toggle", 0),
            preset_spec.get("to_blink", 0),
            preset_spec.get("to_msg_scroll", 0),
            preset_spec.get("toggle_group", 0),
            preset_spec.get("led_color", 0),
            preset_spec.get("toggle_led_color", 0),
            preset_spec.get("shift_led_color", 0),
            preset_spec.get("background_color", 0),
            preset_spec.get("name_color", 0),
            preset_spec.get("toggle_name_color", 0),
            preset_spec.get("shift_name_color", 0),
            preset_spec.get("toggle_background_color", 0),
            preset_spec.get("shift_background_color", 0),
        ]
    )
    payload.extend([0] * 18)  # flags record carries 13 named values + 18 pad = 31 data bytes
    payload.extend([0x7F, 0x06, MC8_PRO_SHORT_NAME_SIZE])
    payload.extend(
        _encode_ascii_payload(
            preset_spec.get("shift_name", ""),
            MC8_PRO_SHORT_NAME_SIZE,
            "shift_name",
        )
    )
    return payload


def _encode_editor_bank_chunk(bank_name: str, bank_number: int) -> list[int]:
    payload = [0x7F, 0x00, 0x01, _validate_7bit_value(bank_number, "bank_number")]
    payload.extend([0x7F, 0x01, 8, 0, 0, 0, 0, 1, 0, 0, 0])
    for message_number in range(MC8_PRO_PRESET_MESSAGE_COUNT):
        payload.extend([0x7F, 0x02, 14])
        payload.extend(
            [
                message_number,
                0,
                0,
                0,
                0,
                1,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        )
    payload.extend([0x7F, 0x03, MC8_PRO_BANK_NAME_SIZE])
    payload.extend(_encode_ascii_payload(bank_name, MC8_PRO_BANK_NAME_SIZE, "bank_name"))
    payload.extend([0x7F, 0x04, MC8_PRO_BANK_NAME_SIZE])
    payload.extend(_editor_blank_name_payload(MC8_PRO_BANK_NAME_SIZE))
    return payload


def _build_editor_current_bank_upload_chunks(
    bank_spec: dict[str, Any],
    bank_number: int,
    include_expression_presets: bool,
    include_bank_chunk: bool = True,
) -> list[dict[str, Any]]:
    preset_lookup = {preset["preset_number"]: preset for preset in bank_spec["presets"]}
    chunks: list[dict[str, Any]] = []

    if include_bank_chunk:
        chunks.append(
            {
                "type": "bank",
                "op3": EDITOR_UPLOAD_BANK_OPCODE_3,
                "op4": 0,
                "op5": 0,
                "payload": _encode_editor_bank_chunk(bank_spec["bank_name"], bank_number),
            }
        )

    for preset_number in range(MC8_PRO_EDITOR_UPLOAD_PRESET_COUNT):
        if preset_number in preset_lookup:
            preset_spec = preset_lookup[preset_number]
        else:
            preset_spec = _editor_default_preset_spec(preset_number)
        chunks.append(
            {
                "type": "preset",
                "op3": EDITOR_UPLOAD_PRESET_OPCODE_3,
                "op4": preset_number,
                "op5": 0,
                "payload": _encode_editor_preset_chunk(preset_spec, bank_number, is_exp=False),
            }
        )

    if include_expression_presets:
        for preset_number in range(MC8_PRO_EDITOR_UPLOAD_EXP_PRESET_COUNT):
            chunks.append(
                {
                    "type": "expPreset",
                    "op3": EDITOR_UPLOAD_EXP_PRESET_OPCODE_3,
                    "op4": preset_number,
                    "op5": 0,
                    "payload": _encode_editor_preset_chunk(
                        _editor_default_preset_spec(preset_number),
                        bank_number,
                        is_exp=True,
                    ),
                }
            )

    return chunks


def _extract_editor_upload_status(response: dict[str, Any]) -> int | None:
    if response.get("function_1") == EDITOR_UPLOAD_OPCODE_2 and response.get("function_2") == 0:
        value = response.get("function_3")
        if value in {
            EDITOR_UPLOAD_STATUS_FAILED,
            EDITOR_UPLOAD_STATUS_CONTROLLER_BACKUP_FAILED,
            EDITOR_UPLOAD_STATUS_COMPLETED,
            EDITOR_UPLOAD_STATUS_REQUEST_NEXT,
        }:
            return value
    return None


def _normalize_editor_upload_status(status: int | None, *, sent_chunks_count: int, finalized: bool) -> int | None:
    if status == EDITOR_UPLOAD_STATUS_FAILED and sent_chunks_count == 0 and not finalized:
        return EDITOR_UPLOAD_STATUS_REQUEST_NEXT
    return status


def _send_editor_sysex_with_retry(
    out_port: mido.ports.BaseOutput,
    request: list[int],
    *,
    context: str,
    retries: int = 3,
    retry_delay_seconds: float = 0.05,
    settle_delay_seconds: float = 0.02,
) -> None:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            out_port.send(mido.Message("sysex", data=request[1:-1]))
            time.sleep(settle_delay_seconds)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            try:
                raw_port = getattr(out_port, "_rt", None)
                if raw_port is not None:
                    raw_port.send_message(request)
                    time.sleep(settle_delay_seconds)
                    return
            except Exception:  # noqa: BLE001
                pass
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to send editor sysex for {context}: {exc}") from exc
            time.sleep(retry_delay_seconds)
    if last_error is not None:
        raise RuntimeError(f"Failed to send editor sysex for {context}: {last_error}") from last_error


def _editor_ack_frame(out_port: mido.ports.BaseOutput, full_frame: list[int]) -> None:
    """Acknowledge a received device frame: func(0, 127, <that frame's checksum byte>)."""
    checksum = full_frame[-2] if len(full_frame) >= 2 else 0
    ack = _build_editor_sysex(function_1=0, function_2=EDITOR_ACK_FUNCTION_2, function_3=checksum)
    _send_editor_sysex_with_retry(out_port, ack, context="ack")


def _editor_drain_and_ack(in_port: mido.ports.BaseInput, out_port: mido.ports.BaseOutput, seconds: float) -> int:
    got = 0
    deadline = time.time() + seconds
    while time.time() < deadline:
        for incoming in in_port.iter_pending():
            if incoming.type != "sysex":
                continue
            full = [0xF0, *list(incoming.data), 0xF7]
            if full[1:4] == MORNINGSTAR_MANUFACTURER_ID:
                got += 1
                _editor_ack_frame(out_port, full)
        time.sleep(0.004)
    return got


def _editor_open_session(in_port: mido.ports.BaseInput, out_port: mido.ports.BaseOutput) -> int:
    """Replay the editor connect handshake so the device will accept a group-7 upload."""
    total = 0
    for f1, f2, f3, model in EDITOR_CONNECT_SEQUENCE:
        req = _build_editor_sysex(function_1=f1, function_2=f2, function_3=f3, model_id=model)
        _send_editor_sysex_with_retry(out_port, req, context="connect")
        total += _editor_drain_and_ack(in_port, out_port, 0.8)
    total += _editor_drain_and_ack(in_port, out_port, 1.0)
    return total


def _run_editor_current_bank_upload(
    chunks: list[dict[str, Any]],
    output_port: str,
    input_port: str,
    timeout_ms: int,
) -> dict[str, Any]:
    """Persist a bank to flash over USB-MIDI cable 0 via the editor group-7 protocol.

    Flow (reverse-engineered from a USBPcap capture and hardware-validated):
    connect handshake -> func(7,0,48,0) start -> per device request-next func(7,0,33): send the next
    chunk then ack func(0,127,checksum) -> func(7,0,49,0) commit. The device ends with a terminal 0x03
    that is benign once all chunks are sent; the data is committed to flash and survives a power-cycle.
    Requires the primary Morningstar port pair (cable 0). NOTE: after an upload the controller stays in
    editor-session mode (real-time 0x70 probes are disabled) until it is power-cycled.
    """
    if timeout_ms < 100 or timeout_ms > 60000:
        raise ValueError("timeout_ms must be in 100..60000")

    out_name = _resolve_out_port(output_port)
    in_name = _resolve_in_port(input_port)
    start_request = _build_editor_sysex(
        function_1=EDITOR_UPLOAD_OPCODE_2, function_2=0, function_3=EDITOR_UPLOAD_START_OPCODE_4, function_4=0
    )
    commit_request = _build_editor_sysex(
        function_1=EDITOR_UPLOAD_OPCODE_2, function_2=0, function_3=EDITOR_UPLOAD_FINALIZE_OPCODE_4, function_4=0
    )

    remaining = [dict(chunk) for chunk in chunks]
    total_chunks = len(chunks)
    sent = 0
    committed = False
    status = None

    with mido.open_input(in_name) as in_port, mido.open_output(out_name) as out_port:
        handshake_frames = _editor_open_session(in_port, out_port)
        _send_editor_sysex_with_retry(out_port, start_request, context="upload start")
        deadline = time.time() + (timeout_ms / 1000.0)

        while time.time() < deadline and status is None:
            for incoming in in_port.iter_pending():
                if incoming.type != "sysex":
                    continue
                full = [0xF0, *list(incoming.data), 0xF7]
                if full[1:4] != MORNINGSTAR_MANUFACTURER_ID or len(full) < 9:
                    continue
                code = (full[6], full[7], full[8])  # (function group, sub, op)
                if code == (EDITOR_UPLOAD_OPCODE_2, 0, EDITOR_UPLOAD_STATUS_COMPLETED):
                    status = "completed"
                    break
                if code == (EDITOR_UPLOAD_OPCODE_2, 0, EDITOR_UPLOAD_STATUS_FAILED):
                    # Terminal 0x03 is the normal end-of-transfer once all chunks are in.
                    status = "completed" if (committed or (not remaining and sent == total_chunks)) else "device_failed"
                    break
                if code == (EDITOR_UPLOAD_OPCODE_2, 0, EDITOR_UPLOAD_STATUS_REQUEST_NEXT):
                    if remaining:
                        c = remaining.pop(0)
                        sent += 1
                        req = _build_editor_sysex(
                            function_1=EDITOR_UPLOAD_OPCODE_2,
                            function_2=c["op3"],
                            function_3=c["op4"],
                            function_4=c["op5"],
                            payload=c["payload"],
                        )
                        _send_editor_sysex_with_retry(out_port, req, context=f"chunk {sent}/{total_chunks}")
                        _editor_ack_frame(out_port, full)
                    elif not committed:
                        committed = True
                        _send_editor_sysex_with_retry(out_port, commit_request, context="commit")
                        _editor_ack_frame(out_port, full)
                    else:
                        _editor_ack_frame(out_port, full)
                else:
                    _editor_ack_frame(out_port, full)
            time.sleep(0.005)

    return {
        "status": status or "timeout",
        "out_port": out_name,
        "in_port": in_name,
        "handshake_frames": handshake_frames,
        "chunks_total": total_chunks,
        "chunks_sent": sent,
        "committed": committed,
        "note": "controller stays in editor-session mode until power-cycled; data is committed to flash",
    }


def _normalize_aux_switch_spec(raw_action: dict[str, Any], index: int) -> dict[str, Any]:
    topology_raw = str(raw_action.get("topology") or "").strip().lower()
    aux_switch_raw = raw_action.get("aux_switch")
    omniport_raw = raw_action.get("omniport")
    slot_raw = raw_action.get("slot")

    if not topology_raw:
        if aux_switch_raw is not None:
            topology_raw = "resistor_ladder_aux"
        elif omniport_raw is not None or slot_raw is not None:
            topology_raw = "trs_aux"

    if topology_raw not in SUPPORTED_AUX_TOPOLOGIES:
        allowed = ", ".join(sorted(SUPPORTED_AUX_TOPOLOGIES))
        raise ValueError(f"aux topology must be one of: {allowed}")

    target: dict[str, Any]
    if topology_raw == "resistor_ladder_aux":
        aux_switch = _parse_int(raw_action.get("aux_switch", index + 1), "aux_switch")
        if aux_switch < 1 or aux_switch > MC8_PRO_RESISTOR_LADDER_AUX_SWITCH_COUNT:
            raise ValueError(
                f"aux_switch must be in 1..{MC8_PRO_RESISTOR_LADDER_AUX_SWITCH_COUNT}"
            )
        target = {
            "topology": topology_raw,
            "omniport": 1,
            "auxSwitch": aux_switch,
        }
    else:
        omniport = _parse_int(raw_action.get("omniport", 1), "omniport")
        if omniport < 1 or omniport > MC8_PRO_OMNIPORT_COUNT:
            raise ValueError(f"omniport must be in 1..{MC8_PRO_OMNIPORT_COUNT}")
        slot_key = str(raw_action.get("slot") or "").strip().lower()
        slot = SUPPORTED_TRS_AUX_SLOTS.get(slot_key)
        if not slot:
            allowed = ", ".join(sorted(SUPPORTED_TRS_AUX_SLOTS))
            raise ValueError(f"slot must be one of: {allowed}")
        target = {
            "topology": topology_raw,
            "omniport": omniport,
            "slot": slot,
        }

    kind = str(raw_action.get("kind") or "").strip().lower()
    if not kind:
        raise ValueError("aux switch entry requires kind")

    if kind == "fixed_function":
        function_name = str(raw_action.get("function") or "").strip().lower()
        if function_name not in SUPPORTED_AUX_FIXED_FUNCTIONS:
            allowed = ", ".join(sorted(SUPPORTED_AUX_FIXED_FUNCTIONS))
            raise ValueError(f"fixed_function must be one of: {allowed}")
        return {
            **target,
            "kind": kind,
            "function": function_name,
            "label": str(raw_action.get("label") or function_name).strip(),
        }

    if kind == "cc":
        return {
            **target,
            "kind": kind,
            "label": str(raw_action.get("label") or f"CC {_parse_int(raw_action.get('cc_number', 0), 'cc_number')}").strip(),
            "midiChannel": _validate_7bit_value(
                _parse_int(raw_action.get("midi_channel", 0), "midi_channel"),
                "midi_channel",
            ),
            "ccNumber": _validate_7bit_value(
                _parse_int(raw_action.get("cc_number", 0), "cc_number"),
                "cc_number",
            ),
            "ccValue": _validate_7bit_value(
                _parse_int(raw_action.get("cc_value", 127), "cc_value"),
                "cc_value",
            ),
            "actionType": _validate_7bit_value(
                _parse_int(raw_action.get("action_type", ACTION_TYPE_PRESS), "action_type"),
                "action_type",
            ),
            "toggleType": _validate_7bit_value(
                _parse_int(raw_action.get("toggle_type", TOGGLE_TYPE_POS_1), "toggle_type"),
                "toggle_type",
            ),
        }

    raise ValueError("aux switch kind must be fixed_function or cc")


def _aux_action_sort_key(action: dict[str, Any]) -> tuple[int, int, int, str]:
    topology_order = 0 if action.get("topology") == "resistor_ladder_aux" else 1
    aux_switch = int(action.get("auxSwitch", 0))
    omniport = int(action.get("omniport", 0))
    slot = str(action.get("slot") or "")
    return (topology_order, omniport, aux_switch, slot)


def _build_draft_omniport_configs(aux_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for action in aux_actions:
        topology = str(action["topology"])
        omniport = int(action["omniport"])
        key = (topology, omniport)
        config = grouped.get(key)
        if config is None:
            config = {
                "omniport": omniport,
                "mode": topology,
            }
            if topology == "resistor_ladder_aux":
                config["switches"] = []
            else:
                config["slots"] = []
            grouped[key] = config

        if topology == "resistor_ladder_aux":
            config["switches"].append(action)
        else:
            config["slots"].append(action)

    configs = list(grouped.values())
    for config in configs:
        if config["mode"] == "resistor_ladder_aux":
            config["switches"].sort(key=lambda item: int(item.get("auxSwitch", 0)))
        else:
            config["slots"].sort(key=lambda item: str(item.get("slot") or ""))
    configs.sort(key=lambda item: (int(item["omniport"]), str(item["mode"])))
    return configs


def _extract_draft_controller_aux_actions(controller_data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    controller_aux_actions: list[dict[str, Any]] = []
    controller_aux_topologies: list[str] = []

    draft_metadata = controller_data.get("draftMetadata")
    if isinstance(draft_metadata, dict):
        inferred_topologies = draft_metadata.get("inferredTopologies", [])
        if isinstance(inferred_topologies, list):
            controller_aux_topologies = [str(item) for item in inferred_topologies]

    if controller_data.get("type") == "controller_settings_all":
        data = controller_data.get("data")
        if isinstance(data, dict):
            resistor_ladder = data.get("resistor_ladder_aux")
            if isinstance(resistor_ladder, dict):
                switches = resistor_ladder.get("switches", [])
                if isinstance(switches, list):
                    controller_aux_actions.extend(
                        [item for item in switches if isinstance(item, dict)]
                    )

            omniports = data.get("omniports")
            if isinstance(omniports, dict):
                aux_switches = omniports.get("auxSwitches", [])
                if isinstance(aux_switches, list):
                    controller_aux_actions.extend(
                        [item for item in aux_switches if isinstance(item, dict)]
                    )

    event_processor = controller_data.get("eventProcessor")
    if isinstance(event_processor, dict):
        aux_switches = event_processor.get("auxSwitches", [])
        if isinstance(aux_switches, list):
            controller_aux_actions.extend(
                [item for item in aux_switches if isinstance(item, dict)]
            )

    return controller_aux_actions, controller_aux_topologies


def _build_draft_controller_data_from_aux_config(aux_actions: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_actions = []
    seen_targets: set[tuple[str, int, int, str]] = set()
    for index, raw_action in enumerate(aux_actions):
        if not isinstance(raw_action, dict):
            raise ValueError(f"aux_config_json[{index}] must be an object")
        normalized = _normalize_aux_switch_spec(raw_action, index)
        target_key = (
            str(normalized["topology"]),
            int(normalized["omniport"]),
            int(normalized.get("auxSwitch", 0)),
            str(normalized.get("slot") or ""),
        )
        if target_key in seen_targets:
            raise ValueError("Duplicate aux target entry in aux_config_json")
        seen_targets.add(target_key)
        normalized_actions.append(normalized)

    normalized_actions.sort(key=_aux_action_sort_key)
    omniport_configs = _build_draft_omniport_configs(normalized_actions)
    inferred_topologies = sorted({str(action["topology"]) for action in normalized_actions})
    trs_aux_actions = [
        action for action in normalized_actions if action.get("topology") == "trs_aux"
    ]
    resistor_ladder_actions = [
        action
        for action in normalized_actions
        if action.get("topology") == "resistor_ladder_aux"
    ]
    return {
        "type": "controller_settings_all",
        "data": {
            "omniports": {
                "schemaVersion": DRAFT_CONTROLLER_DATA_VERSION,
                "source": "inferred-from-editor-controller_settings_all",
                "omniportConfigs": omniport_configs,
                "auxSwitches": trs_aux_actions,
            },
            "resistor_ladder_aux": {
                "schemaVersion": DRAFT_CONTROLLER_DATA_VERSION,
                "source": "inferred-from-editor-controller_settings_all",
                "omniport": 1,
                "switches": resistor_ladder_actions,
            },
        },
        "draftMetadata": {
            "compatibility": "draft-controller-data-only",
            "inferredTopologies": inferred_topologies,
            "draftAuxSummary": normalized_actions,
            "notes": [
                "This structure is intended for backup generation and reverse engineering.",
                "The top-level wrapper mirrors the editor's controller_settings_all serializer path.",
                "aux_switch entries are modeled as Omniport 1 resistor-ladder aux switches.",
                "TRS aux entries are modeled per omniport slot: tip, ring, or tip+ring.",
                "Live controller-settings restore transport is still unresolved.",
            ],
        },
    }


def _build_controller_data_tool_result(
    controller_data: dict[str, Any],
    pretty: bool,
) -> dict[str, Any]:
    aux_actions = controller_data["draftMetadata"].get("draftAuxSummary", [])
    inferred_topologies = controller_data["draftMetadata"].get("inferredTopologies", [])

    return {
        "status": "completed",
        "decoded": {
            "kind": "controller-data",
            "draft": True,
            "schema_version": DRAFT_CONTROLLER_DATA_VERSION,
            "wrapper_type": controller_data.get("type", ""),
            "inferred_topologies": inferred_topologies,
            "aux_switch_count": len(aux_actions),
            "aux_actions": [
                {
                    "topology": action.get("topology", ""),
                    "omniport": action.get("omniport", 0),
                    "aux_switch": action.get("auxSwitch", 0),
                    "slot": action.get("slot", ""),
                    "kind": action["kind"],
                    "summary": action.get("function") or f"CC {action.get('ccNumber', 0)}",
                }
                for action in aux_actions
            ],
        },
        "controller_data_json": _dump_json(controller_data, pretty=pretty),
    }


def _dump_json(value: Any, pretty: bool) -> str:
    if pretty:
        return json.dumps(value, indent=2)
    return json.dumps(value, separators=(",", ":"))


def _format_tool_reference_annotation(annotation: Any) -> str:
    if annotation is inspect.Signature.empty:
        return "Any"
    if annotation is None:
        return "None"
    rendered = str(annotation)
    rendered = rendered.replace("typing.", "")
    rendered = rendered.replace("<class '", "")
    rendered = rendered.replace("'>", "")
    return rendered


def _format_tool_reference_default(value: Any) -> str:
    if value is inspect.Signature.empty:
        return ""
    return repr(value)


def _tool_reference_function_names() -> list[str]:
    return list(TOOL_REFERENCE_METADATA.keys())


def _tool_reference_functions() -> list[tuple[str, Any]]:
    return [(name, globals()[name]) for name in _tool_reference_function_names()]


def generate_tool_reference_markdown() -> str:
    """Render the operator-facing Markdown reference for the MCP tools exposed by this server."""
    grouped: dict[str, list[str]] = {group: [] for group in TOOL_REFERENCE_GROUP_ORDER}
    for tool_name in _tool_reference_function_names():
        metadata = TOOL_REFERENCE_METADATA[tool_name]
        grouped.setdefault(metadata["group"], []).append(tool_name)

    lines = [
        "# MC8 MCP Tool Reference",
        "",
        "This file is generated from `morningstar_mc8_mcp.py`. It documents the regular MCP tool surface exposed by the Morningstar MC8 Pro server without introducing a custom API layer.",
        "",
        "## Server Status",
        "",
        "- Runtime model: regular MCP server over stdio",
        "- Primary server file: `morningstar_mc8_mcp.py`",
        "- Tool count: {}".format(len(TOOL_REFERENCE_METADATA)),
        "- Validated Windows ports in this workspace: output `Morningstar MC8 Pro 3`, input `Morningstar MC8 Pro 2`",
        "",
        "## Categories",
        "",
    ]

    for group in TOOL_REFERENCE_GROUP_ORDER:
        lines.append(f"- {group}: {len(grouped.get(group, []))} tools")

    lines.extend(
        [
            "",
            "## Safety Levels",
            "",
            "- `read-only`: queries device state without modifying controller data",
            "- `write`: updates controller state or persistent data",
            "- `navigation`: changes the current controller view or bank selection",
            "- `experimental`: write surface exists, but parts of the protocol remain inferred or lightly verified",
            "- `offline-json`: transforms backup JSON locally without device I/O",
            "",
            "## Transport Notes",
            "",
            "- `request-response`: sends a SysEx request and waits for a matching reply or ACK",
            "- `fire-and-forget`: sends a controller command without waiting for an ACK",
            "- `mixed`: performs writes plus optional follow-up probe reads",
            "- `local-only`: performs no device I/O",
            "",
            "## Recommended Workflows",
            "",
            "### 1. Confirm ports, then read the active bank",
            "",
            "```python",
            "list_midi_ports()",
            "probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "```",
            "",
            "Use this path first when a session starts. It confirms which virtual ports are available and gives you a safe readback anchor before any navigation or writes.",
            "",
            "### 2. Test a label change without saving it",
            "",
            "```python",
            "set_current_bank_name(bank_name='TEST BANK', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "```",
            "",
            "Use temporary overrides when validating framing, port selection, or naming logic. Unsaved names revert on bank change.",
            "",
            "### 3. Program the selected bank from JSON and verify it",
            "",
            "```python",
            "program_current_bank_from_json(bank_json='{\"bank_name\":\"AFX 001-008\",\"presets\":[]}', save=False, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2', midi_channel=1, verify=True)",
            "```",
            "",
            "This is the highest-level live programming workflow in the current MCP surface. Keep `verify=True` unless you already have a faster external verification loop.",
            "",
            "### 4. Build and inspect backup JSON offline",
            "",
            "```python",
            "build_current_bank_backup_json(bank_json='{\"bank_name\":\"AFX 001-008\",\"presets\":[]}', pretty=True)",
            "inspect_backup_json(backup_json='{}')",
            "```",
            "",
            "Use the offline backup helpers when you need Morningstar-shaped JSON containers without touching the device.",
            "",
            "### 5. Navigate one bank, then verify the move",
            "",
            "```python",
            "before = probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "bank_up(output_port='Morningstar MC8 Pro 3')",
            "after = probe_get_current_bank_name(output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "```",
            "",
            "Navigation calls are fire-and-forget in this setup, so use a follow-up bank-name read to confirm the controller actually moved.",
            "",
            "### 6. Write a preset message slot and read back a nearby label",
            "",
            "```python",
            "set_preset_message_cc(preset='A', message_slot=0, cc_number=34, cc_value=0, midi_channel=0, save=True, output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "probe_get_preset_short_name(preset='A', output_port='Morningstar MC8 Pro 3', input_port='Morningstar MC8 Pro 2')",
            "```",
            "",
            "Message writes do not have a full readback surface today, so pair them with adjacent observable checks such as bank-name or preset-label reads.",
            "",
        ]
    )

    for group in TOOL_REFERENCE_GROUP_ORDER:
        tool_names = grouped.get(group, [])
        if not tool_names:
            continue
        lines.append(f"## {group}")
        lines.append("")
        for tool_name in tool_names:
            func = globals()[tool_name]
            metadata = TOOL_REFERENCE_METADATA[tool_name]
            signature = inspect.signature(func)
            lines.append(f"### `{tool_name}`")
            lines.append("")
            if func.__doc__:
                lines.append(func.__doc__.strip())
                lines.append("")
            lines.append(f"- Safety: `{metadata['safety']}`")
            lines.append(f"- Verification: `{metadata['verification']}`")
            lines.append(f"- Transport: `{metadata['transport']}`")
            lines.append(f"- Returns: {metadata['returns']}")
            lines.append("")
            lines.append("**Signature**")
            lines.append("")
            lines.append("```python")
            lines.append(f"{tool_name}{signature}")
            lines.append("```")
            lines.append("")
            lines.append("**Parameters**")
            lines.append("")
            lines.append("| Name | Type | Required | Default |")
            lines.append("| --- | --- | --- | --- |")
            for parameter in signature.parameters.values():
                required = parameter.default is inspect.Signature.empty
                lines.append(
                    "| `{}` | `{}` | {} | `{}` |".format(
                        parameter.name,
                        _format_tool_reference_annotation(parameter.annotation),
                        "yes" if required else "no",
                        _format_tool_reference_default(parameter.default),
                    )
                )
            lines.append("")
            if metadata["notes"]:
                lines.append("**Notes**")
                lines.append("")
                for note in metadata["notes"]:
                    lines.append(f"- {note}")
                lines.append("")
            lines.append("**Example**")
            lines.append("")
            lines.append("```python")
            lines.append(metadata["example"])
            lines.append("```")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@mcp.tool()
def list_midi_ports() -> dict[str, Any]:
    """Report the MIDI ports visible to this host and highlight likely Morningstar candidates."""
    inputs = _list_inputs()
    outputs = _list_outputs()
    return {
        "inputs": inputs,
        "outputs": outputs,
        "morningstar_candidates": {
            "inputs": _candidate_ports(inputs),
            "outputs": _candidate_ports(outputs),
        },
        "defaults": {
            "MORNINGSTAR_MC8_MIDI_IN": DEFAULT_IN_PORT,
            "MORNINGSTAR_MC8_MIDI_OUT": DEFAULT_OUT_PORT,
        },
        "note": "Port 1 is typically reserved for the Morningstar editor. Prefer a different virtual port for probes when available.",
    }


@mcp.tool()
def get_sysex_reference() -> dict[str, Any]:
    """Return the SysEx framing constants and capability summary that this MCP server is built around."""
    return {
        "manufacturer_id": MORNINGSTAR_MANUFACTURER_ID,
        "model_id": MC8_PRO_MODEL_ID,
        "opcode_1": MORNINGSTAR_OPCODE_1,
        "payload_start_index": 16,
        "read_only_capabilities": READ_ONLY_CAPABILITIES,
        "ack_codes": ACK_CODES,
        "example_request_get_controller_info": _bytes_to_hex(_build_request(op2=0x32, txn_id=1)),
    }


@mcp.tool()
def probe_get_controller_info(
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 1,
) -> dict[str, Any]:
    """Query controller identity and limits so you can verify the device and payload sizes before writing."""
    result = _run_probe(
        op2=0x32,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    payload = response["payload"]
    if len(payload) < 9:
        raise RuntimeError(f"Unexpected controller info payload size: {len(payload)}")

    result["decoded"] = {
        "model_id": payload[0],
        "firmware_version": ".".join(str(value) for value in payload[1:5]),
        "total_messages_per_preset": payload[5],
        "preset_name_size": payload[6],
        "preset_long_name_size": payload[7],
        "bank_name_size": payload[8],
    }
    return result


@mcp.tool()
def probe_get_current_bank_name(
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 2,
) -> dict[str, Any]:
    """Read the name of the bank that is currently selected on the controller."""
    result = _run_probe(
        op2=0x30,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    result["decoded"] = {
        "payload_size": response["opcode_4"],
        "bank_name": _decode_ascii_payload(response["payload"]),
    }
    return result


def _probe_get_preset_name(
    op2: int,
    preset: str,
    output_port: str,
    input_port: str,
    timeout_ms: int,
    txn_id: int,
    name_key: str,
) -> dict[str, Any]:
    preset_number = _parse_preset_id(preset)
    result = _run_probe(
        op2=op2,
        op3=preset_number,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    result["decoded"] = {
        "preset": preset,
        "preset_number": preset_number,
        "payload_size": response["opcode_4"],
        name_key: _decode_ascii_payload(response["payload"]),
    }
    return result


@mcp.tool()
def probe_get_preset_short_name(
    preset: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 3,
) -> dict[str, Any]:
    """Read the short label for one preset in the currently selected bank. Preset A maps to slot 0."""
    return _probe_get_preset_name(
        op2=0x21,
        preset=preset,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        name_key="short_name",
    )


@mcp.tool()
def probe_get_preset_toggle_name(
    preset: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 4,
) -> dict[str, Any]:
    """Read the toggle label for one preset in the currently selected bank. Preset A maps to slot 0."""
    return _probe_get_preset_name(
        op2=0x22,
        preset=preset,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        name_key="toggle_name",
    )


@mcp.tool()
def probe_get_preset_long_name(
    preset: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 5,
) -> dict[str, Any]:
    """Read the long label for one preset in the currently selected bank. Preset A maps to slot 0."""
    return _probe_get_preset_name(
        op2=0x23,
        preset=preset,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        name_key="long_name",
    )


@mcp.tool()
def probe_get_toggle_states(
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 6,
) -> dict[str, Any]:
    """Read the toggle-state bytes for every preset in the currently selected bank."""
    result = _run_probe(
        op2=0x31,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    payload = response["payload"]
    decoded = []
    for index, value in enumerate(payload):
        decoded.append(
            {
                "preset_number": index,
                "preset_label": chr(ord("A") + index) if index < 26 else str(index),
                "raw": value,
                "toggled": value == 0x7F,
            }
        )
    result["decoded"] = {
        "payload_size": response["opcode_4"],
        "states": decoded,
    }
    return result


@mcp.tool()
def probe_get_controller_settings_all(
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 7,
) -> dict[str, Any]:
    """Request the controller-settings-all container through the editor-backed request function opcode."""
    result = _run_probe(
        op2=0x00,
        op3=REQUEST_CONTROLLER_SETTINGS_ALL,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    result["decoded"] = {
        "request": "controller_settings_all",
        "payload_size": len(response["payload"]),
        "opcode_2": response["opcode_2"],
        "opcode_3": response["opcode_3"],
    }
    return result


@mcp.tool()
def probe_get_controller_omniport_data(
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 8,
) -> dict[str, Any]:
    """Request the Omniport controller-settings section through the editor-backed request function opcode."""
    result = _run_probe(
        op2=0x00,
        op3=REQUEST_OMNIPORT_DATA,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    response = _ensure_success(result["response"])
    result["decoded"] = {
        "request": "omniport_data",
        "payload_size": len(response["payload"]),
        "opcode_2": response["opcode_2"],
        "opcode_3": response["opcode_3"],
    }
    return result


@mcp.tool()
def set_current_bank_name(
    bank_name: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 20,
) -> dict[str, Any]:
    """Rename the current bank, either as a saved edit or as a temporary override that clears on bank change."""
    payload = _encode_ascii_payload(
        bank_name,
        size=MC8_PRO_BANK_NAME_SIZE,
        label="bank_name",
    )
    result = _run_write(
        op2=0x10,
        op4=_save_opcode(save),
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "bank_name": bank_name,
        "saved": save,
    }
    return result


@mcp.tool()
def set_preset_short_name(
    preset: str,
    short_name: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 21,
) -> dict[str, Any]:
    """Update one preset's short label in the current bank."""
    return _write_preset_name(
        op2=0x01,
        preset=preset,
        value=short_name,
        size=MC8_PRO_SHORT_NAME_SIZE,
        decoded_key="short_name",
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )


@mcp.tool()
def set_preset_toggle_name(
    preset: str,
    toggle_name: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 22,
) -> dict[str, Any]:
    """Update one preset's toggle label in the current bank."""
    return _write_preset_name(
        op2=0x02,
        preset=preset,
        value=toggle_name,
        size=MC8_PRO_TOGGLE_NAME_SIZE,
        decoded_key="toggle_name",
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )


@mcp.tool()
def set_preset_long_name(
    preset: str,
    long_name: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 23,
) -> dict[str, Any]:
    """Update one preset's long label in the current bank."""
    return _write_preset_name(
        op2=0x03,
        preset=preset,
        value=long_name,
        size=MC8_PRO_LONG_NAME_SIZE,
        decoded_key="long_name",
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )


@mcp.tool()
def display_message(
    message: str,
    duration_ms: int = 1000,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 24,
) -> dict[str, Any]:
    """Show a temporary message on the MC8 display without changing stored bank data."""
    if duration_ms < 0 or duration_ms > 12700:
        raise ValueError("duration_ms must be between 0 and 12700")

    duration_units = duration_ms // 100
    payload = _encode_ascii_message(
        message,
        size=MC8_PRO_LCD_MESSAGE_SIZE,
        label="message",
    )
    result = _send_write_without_response(
        op2=0x11,
        op4=duration_units,
        payload=payload,
        output_port=output_port,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "message": message,
        "duration_ms": duration_units * 100,
    }
    return result


@mcp.tool()
def bank_up(
    output_port: str = "",
    txn_id: int = 40,
) -> dict[str, Any]:
    """Advance the controller to the next bank using Morningstar's bank-up function."""
    result = _send_controller_function(
        function_id=CONTROLLER_FUNCTION_BANK_UP,
        value=0,
        output_port=output_port,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "function": "bank_up",
    }
    return result


@mcp.tool()
def bank_down(
    output_port: str = "",
    txn_id: int = 41,
) -> dict[str, Any]:
    """Move the controller to the previous bank using Morningstar's bank-down function."""
    result = _send_controller_function(
        function_id=CONTROLLER_FUNCTION_BANK_DOWN,
        value=0,
        output_port=output_port,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "function": "bank_down",
    }
    return result


@mcp.tool()
def toggle_page(
    output_port: str = "",
    txn_id: int = 42,
) -> dict[str, Any]:
    """Toggle between the controller's page views for the current bank."""
    result = _send_controller_function(
        function_id=CONTROLLER_FUNCTION_TOGGLE_PAGE,
        value=0,
        output_port=output_port,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "function": "toggle_page",
    }
    return result


@mcp.tool()
def send_editor_upload_complete_signal(
    output_port: str = "",
    txn_id: int = 43,
) -> dict[str, Any]:
    """Send the editor's observed post-upload completion signal as a fire-and-forget probe."""
    result = _send_function_without_response(
        op2=0x07,
        op3=0x00,
        op4=0x31,
        op5=0x00,
        output_port=output_port,
        txn_id=txn_id,
    )
    result["decoded"] = {
        "function": "editor_upload_complete_signal",
    }
    return result


@mcp.tool()
def set_preset_message_raw(
    preset: str,
    message_slot: int,
    message_type: int,
    payload_json: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 33,
) -> dict[str, Any]:
    """Write a raw preset-message payload when no safer typed helper exists."""
    payload = _parse_json_argument(payload_json, "payload_json")
    if not isinstance(payload, list):
        raise ValueError("payload_json must decode to a JSON array of 7-bit integers")

    result = _write_preset_message(
        preset=preset,
        message_slot=message_slot,
        message_type=_validate_7bit_value(message_type, "message_type"),
        payload=_validate_raw_payload([_parse_int(value, "payload value") for value in payload]),
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )
    result["decoded"].update(
        {
            "mode": "raw",
        }
    )
    return result


@mcp.tool()
def set_preset_message_note(
    preset: str,
    message_slot: int,
    note_number: int,
    velocity: int,
    midi_channel: int,
    save: bool = True,
    action_type: int = ACTION_TYPE_PRESS,
    toggle_type: int = TOGGLE_TYPE_POS_1,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 34,
) -> dict[str, Any]:
    """Write an inferred Note message through the experimental raw-message path. Treat the message-type mapping as unverified."""
    payload = _build_note_message_payload(
        note_number=note_number,
        velocity=velocity,
        midi_channel=midi_channel,
        action_type=action_type,
        toggle_type=toggle_type,
    )
    result = _write_preset_message(
        preset=preset,
        message_slot=message_slot,
        message_type=0x03,
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )
    result["decoded"].update(
        {
            "mode": "experimental_note",
            "note_number": note_number,
            "velocity": velocity,
            "midi_channel": midi_channel,
            "action_type": action_type,
            "toggle_type": toggle_type,
        }
    )
    return result


@mcp.tool()
def set_controller_omniport_data_raw(
    payload_json: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 43,
) -> dict[str, Any]:
    """Write a raw Omniport controller-settings payload through the editor-backed save opcode."""
    return _write_controller_settings_section_raw(
        payload_json=payload_json,
        section_name="omniport_data",
        op3=WRITE_CONTROLLER_OMNIPORT_DATA,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )


@mcp.tool()
def set_controller_event_processor_raw(
    payload_json: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 44,
) -> dict[str, Any]:
    """Write a raw event-processor payload through the editor-backed save opcode."""
    return _write_controller_settings_section_raw(
        payload_json=payload_json,
        section_name="event_processor",
        op3=WRITE_CONTROLLER_EVENT_PROCESSOR_DATA,
        op4=0,
        op5=0,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )


@mcp.tool()
def set_controller_resistor_ladder_aux_raw(
    payload_json: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 45,
) -> dict[str, Any]:
    """Write a raw resistor-ladder aux payload through the editor-backed save opcode."""
    return _write_controller_settings_section_raw(
        payload_json=payload_json,
        section_name="resistor_ladder_aux",
        op3=WRITE_RESISTOR_LADDER_AUX_SWITCH_DATA,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )


@mcp.tool()
def set_controller_midi_clock_slots_raw(
    payload_json: str,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 46,
) -> dict[str, Any]:
    """Write a raw MIDI clock slots payload through the editor-backed save opcode."""
    return _write_controller_settings_section_raw(
        payload_json=payload_json,
        section_name="midi_clock_slots",
        op3=WRITE_MIDI_CLOCK_SLOTS_DATA,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
    )


@mcp.tool()
def set_preset_message_pc(
    preset: str,
    message_slot: int,
    program: int,
    midi_channel: int,
    save: bool = True,
    action_type: int = ACTION_TYPE_PRESS,
    toggle_type: int = TOGGLE_TYPE_POS_1,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 30,
) -> dict[str, Any]:
    """Write one documented Program Change message into a preset message slot."""
    payload = _build_pc_message_payload(
        program=program,
        midi_channel=midi_channel,
        action_type=action_type,
        toggle_type=toggle_type,
    )
    result = _write_preset_message(
        preset=preset,
        message_slot=message_slot,
        message_type=MESSAGE_TYPE_PC,
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )
    result["decoded"].update(
        {
            "program": program,
            "midi_channel": midi_channel,
            "action_type": action_type,
            "toggle_type": toggle_type,
        }
    )
    return result


@mcp.tool()
def set_preset_message_cc(
    preset: str,
    message_slot: int,
    cc_number: int,
    cc_value: int,
    midi_channel: int,
    save: bool = True,
    action_type: int = ACTION_TYPE_PRESS,
    toggle_type: int = TOGGLE_TYPE_POS_1,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 31,
) -> dict[str, Any]:
    """Write one documented Control Change message into a preset message slot."""
    payload = _build_cc_message_payload(
        cc_number=cc_number,
        cc_value=cc_value,
        midi_channel=midi_channel,
        action_type=action_type,
        toggle_type=toggle_type,
    )
    result = _write_preset_message(
        preset=preset,
        message_slot=message_slot,
        message_type=MESSAGE_TYPE_CC,
        payload=payload,
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
        txn_id=txn_id,
        save=save,
    )
    result["decoded"].update(
        {
            "cc_number": cc_number,
            "cc_value": cc_value,
            "midi_channel": midi_channel,
            "action_type": action_type,
            "toggle_type": toggle_type,
        }
    )
    return result


@mcp.tool()
def set_preset_bank_select_and_program_change(
    preset: str,
    start_message_slot: int,
    bank_msb: int,
    program: int,
    midi_channel: int,
    save: bool = True,
    include_bank_lsb: bool = False,
    bank_lsb: int = 0,
    action_type: int = ACTION_TYPE_PRESS,
    toggle_type: int = TOGGLE_TYPE_POS_1,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    txn_id: int = 32,
) -> dict[str, Any]:
    """Write CC0, optional CC32, and Program Change into adjacent slots for one preset."""
    slot_number = _parse_message_slot(start_message_slot)
    writes = [
        set_preset_message_cc(
            preset=preset,
            message_slot=slot_number,
            cc_number=0,
            cc_value=bank_msb,
            midi_channel=midi_channel,
            save=save,
            action_type=action_type,
            toggle_type=toggle_type,
            output_port=output_port,
            input_port=input_port,
            timeout_ms=timeout_ms,
            txn_id=txn_id,
        )
    ]

    next_slot = slot_number + 1
    if include_bank_lsb:
        if next_slot > 15:
            raise ValueError("Not enough message slots for CC0, CC32, and PC starting at this slot")
        writes.append(
            set_preset_message_cc(
                preset=preset,
                message_slot=next_slot,
                cc_number=32,
                cc_value=bank_lsb,
                midi_channel=midi_channel,
                save=save,
                action_type=action_type,
                toggle_type=toggle_type,
                output_port=output_port,
                input_port=input_port,
                timeout_ms=timeout_ms,
                txn_id=min(txn_id + 1, 127),
            )
        )
        next_slot += 1

    if next_slot > 15:
        raise ValueError("Not enough message slots for bank select plus program change starting at this slot")

    writes.append(
        set_preset_message_pc(
            preset=preset,
            message_slot=next_slot,
            program=program,
            midi_channel=midi_channel,
            save=save,
            action_type=action_type,
            toggle_type=toggle_type,
            output_port=output_port,
            input_port=input_port,
            timeout_ms=timeout_ms,
            txn_id=min(txn_id + len(writes), 127),
        )
    )

    return {
        "status": "completed",
        "writes": writes,
        "decoded": {
            "preset": preset,
            "start_message_slot": slot_number,
            "bank_msb": bank_msb,
            "include_bank_lsb": include_bank_lsb,
            "bank_lsb": bank_lsb if include_bank_lsb else None,
            "program": program,
            "midi_channel": midi_channel,
            "saved": save,
        },
    }


@mcp.tool()
def program_current_bank_from_json(
    bank_json: str,
    save: bool = True,
    output_port: str = "",
    input_port: str = "",
    midi_channel: int = 1,
    verify: bool = True,
) -> dict[str, Any]:
    """Program the currently selected bank from a supported JSON spec and optionally verify the result with live readback."""
    if midi_channel < 1 or midi_channel > 16:
        raise ValueError("midi_channel must be in 1..16")

    bank_spec = _normalize_supported_bank_spec(_parse_json_argument(bank_json, "bank_json"))
    writes = _program_current_bank_from_spec(
        bank_spec=bank_spec,
        output_port=output_port,
        input_port=input_port,
        save=save,
        default_midi_channel=midi_channel - 1,
    )

    result: dict[str, Any] = {
        "status": "completed",
        "writes": len(writes),
        "decoded": {
            "bank_name": bank_spec["bank_name"],
            "preset_count": len(bank_spec["presets"]),
            "save": save,
        },
    }

    if verify:
        current_bank = probe_get_current_bank_name(output_port=output_port, input_port=input_port)
        expected_preset_a = next(
            (preset["short_name"] for preset in bank_spec["presets"] if preset["preset"] == "A"),
            "",
        )
        current_preset_a = probe_get_preset_short_name(
            preset="A",
            output_port=output_port,
            input_port=input_port,
        )
        result["verification"] = {
            "bank_name": current_bank["decoded"]["bank_name"],
            "preset_a": current_preset_a["decoded"]["short_name"],
            "verified": current_bank["decoded"]["bank_name"] == bank_spec["bank_name"]
            and current_preset_a["decoded"]["short_name"] == expected_preset_a,
        }

    return result


@mcp.tool()
def upload_current_bank_from_json(
    bank_json: str,
    bank_number: int = 0,
    output_port: str = "",
    input_port: str = "",
    timeout_ms: int = 15000,
    include_expression_presets: bool = True,
    include_bank_chunk: bool = True,
    expect_current_bank_name: str = "",
) -> dict[str, Any]:
    """Persist a bank to the MC8's FLASH over USB-MIDI via the editor group-7 protocol.

    Hardware-validated 2026-07-03: writes survive a power-cycle. Runs a connect handshake, then the
    ACK-driven upload loop (see _run_editor_current_bank_upload), on the PRIMARY Morningstar port pair
    (cable 0) - pass output_port/input_port='' to auto-select it. bank_number is 0-based (bank 1 = 0).
    A "completed" status (incl. the benign terminal 0x03) means the data was committed to flash.

    WARNING: this writes to the bank the controller is CURRENTLY NAVIGATED TO. `bank_number` is only
    embedded as chunk metadata - it does NOT choose the target bank. Uploading while parked on the
    wrong bank silently corrupts that bank (this is how the factory layout got shifted). Prefer the
    guarded `safe_flash_bank` tool, or pass `expect_current_bank_name` here: when set, the current bank
    name is probed and MUST match before any write - a mismatch raises BankPositionError and nothing is
    sent, converting silent corruption into a safe abort.

    IMPORTANT: the controller stays in editor-session mode (0x70 real-time probes disabled) until you
    power-cycle it after the upload. Unlike the 0x70 setters, this is the only MCP path that persists.
    """
    if expect_current_bank_name:
        _assert_current_bank_name(expect_current_bank_name, output_port, input_port)
    bank_spec = _normalize_supported_bank_spec(_parse_json_argument(bank_json, "bank_json"))
    upload = _run_editor_current_bank_upload(
        chunks=_build_editor_current_bank_upload_chunks(
            bank_spec=bank_spec,
            bank_number=_validate_7bit_value(bank_number, "bank_number"),
            include_expression_presets=include_expression_presets,
            include_bank_chunk=include_bank_chunk,
        ),
        output_port=output_port,
        input_port=input_port,
        timeout_ms=timeout_ms,
    )
    upload["decoded"] = {
        "bank_name": bank_spec["bank_name"],
        "preset_count": len(bank_spec["presets"]),
        "bank_number": bank_number,
        "include_expression_presets": include_expression_presets,
        "include_bank_chunk": include_bank_chunk,
    }
    return upload


class BankPositionError(RuntimeError):
    """Raised when the controller is not confirmed to be on the intended bank before a flash write."""


def _first_morningstar_input() -> str:
    names = _list_inputs()
    for name in names:
        if name.startswith("Morningstar MC8 Pro"):
            return name
    candidates = _candidate_ports(names)
    if candidates:
        return candidates[0]
    raise ValueError("No Morningstar MC8 input port found. Use list_midi_ports.")


def _first_morningstar_output() -> str:
    names = _list_outputs()
    for name in names:
        if name.startswith("Morningstar MC8 Pro"):
            return name
    candidates = _candidate_ports(names)
    if candidates:
        return candidates[0]
    raise ValueError("No Morningstar MC8 output port found. Use list_midi_ports.")


def _probe_bank_name_now(output_port: str, input_port: str) -> str:
    """Best-effort read of the current bank name; '' if the probe times out (e.g. editor-session mode)."""
    try:
        return probe_get_current_bank_name(
            output_port=output_port, input_port=input_port
        )["decoded"]["bank_name"].strip()
    except Exception:  # noqa: BLE001 - timeout / session-mode / port errors all mean "unknown"
        return ""


def _assert_current_bank_name(
    expected: str,
    output_port: str = "",
    input_port: str = "",
    retries: int = 6,
    delay_seconds: float = 0.4,
) -> str:
    """Probe the current bank name and require it to equal `expected`, else raise BankPositionError.

    This is the core anti-corruption guard: it runs BEFORE any flash write so that a navigation error
    aborts loudly instead of overwriting the wrong bank. Empty/timeout reads (the controller sitting in
    editor-session mode with probes disabled) never satisfy the check - power-cycle first.
    """
    want = expected.strip()
    last = ""
    for attempt in range(retries):
        last = _probe_bank_name_now(output_port, input_port)
        if last and last == want:
            return last
        if attempt < retries - 1:
            time.sleep(delay_seconds)
    raise BankPositionError(
        f"Refusing to flash: current bank reads {last!r} but expected {want!r}. "
        "Aborted before sending anything so the wrong bank is not corrupted. "
        "Re-navigate to the intended bank (or power-cycle if the controller is in editor-session mode) and retry."
    )


def _navigate_steps(delta: int, output_port: str, delay_seconds: float) -> None:
    step = bank_up if delta > 0 else bank_down
    for _ in range(abs(delta)):
        step(output_port=output_port)
        time.sleep(delay_seconds)


def _goto_bank_by_anchor(
    anchor_bank_name: str,
    anchor_bank_number: int,
    target_bank_number: int,
    output_port: str,
    input_port: str,
    delay_seconds: float,
    max_walk: int = 130,
) -> dict[str, Any]:
    """Establish absolute position by walking bank-up to a KNOWN-UNIQUE landmark, then step to target.

    Name->number lookup is deliberately avoided: corrupted banks report the wrong name, so only a
    landmark name the caller vouches is unique and correct is trusted. Bank navigation wraps 1<->128,
    so a bounded bank-up walk always meets the landmark if it exists. Returns the walk trail.
    """
    landmark = anchor_bank_name.strip()
    walked = 0
    for _ in range(max_walk):
        if _probe_bank_name_now(output_port, input_port) == landmark:
            break
        bank_up(output_port=output_port)
        time.sleep(delay_seconds)
        walked += 1
    else:
        raise BankPositionError(
            f"Could not find anchor bank {landmark!r} within {max_walk} bank-up steps; aborting before any write."
        )
    delta = target_bank_number - anchor_bank_number
    _navigate_steps(delta, output_port, delay_seconds)
    return {"anchor_walk_steps": walked, "steps_from_anchor": delta}


@mcp.tool()
def safe_flash_bank(
    bank_json: str,
    target_bank_number: int,
    expect_current_bank_name: str,
    anchor_bank_name: str = "",
    anchor_bank_number: int = 0,
    output_port: str = "",
    input_port: str = "",
    nav_delay_ms: int = 400,
    timeout_ms: int = 20000,
    include_expression_presets: bool = True,
    include_bank_chunk: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Guarded, position-verified flash write of ONE bank - the safe way to persist a bank.

    Prevents the off-by-one bank corruption that the raw `upload_current_bank_from_json` allows. Steps:
      1. Resolve the primary (cable 0) Morningstar port pair automatically, tolerating USB re-enumeration.
      2. If `anchor_bank_name` is given, establish absolute position by walking bank-up to that
         KNOWN-UNIQUE, CORRECT landmark (at `anchor_bank_number`, 1-based), then step to the target.
         Omit the anchor only when the controller is already parked on the target bank.
      3. GUARD: probe the current bank name and require it to equal `expect_current_bank_name` (the name
         the target bank reads RIGHT NOW, before the fix). On mismatch it raises BankPositionError and
         writes nothing.
      4. Flash the bank via the group-7 protocol, then send the post-upload completion signal.

    `dry_run=True` performs navigation + the guard and reports what it WOULD write, without flashing (no
    session-mode lock) - use it to rehearse safely. After a real write the controller is locked in
    editor-session mode: POWER-CYCLE the MC8 before flashing another bank or verifying. Flash one bank
    per power-cycle. `target_bank_number` is 1-based; the 0-based value is embedded as chunk metadata.
    """
    if target_bank_number < 1 or target_bank_number > 128:
        raise ValueError("target_bank_number must be in 1..128")
    if not expect_current_bank_name.strip():
        raise ValueError("expect_current_bank_name is required - it is the guard that prevents wrong-bank writes")

    out_name = _resolve_out_port(output_port) if output_port else _first_morningstar_output()
    in_name = _resolve_in_port(input_port) if input_port else _first_morningstar_input()
    delay_seconds = max(nav_delay_ms, 0) / 1000.0

    nav: dict[str, Any] = {"anchored": False}
    if anchor_bank_name.strip():
        if anchor_bank_number < 1 or anchor_bank_number > 128:
            raise ValueError("anchor_bank_number must be in 1..128 when anchor_bank_name is set")
        nav = _goto_bank_by_anchor(
            anchor_bank_name=anchor_bank_name,
            anchor_bank_number=anchor_bank_number,
            target_bank_number=target_bank_number,
            output_port=out_name,
            input_port=in_name,
            delay_seconds=delay_seconds,
        )
        nav["anchored"] = True

    confirmed = _assert_current_bank_name(expect_current_bank_name, out_name, in_name)

    result: dict[str, Any] = {
        "out_port": out_name,
        "in_port": in_name,
        "target_bank_number": target_bank_number,
        "confirmed_current_bank_name": confirmed,
        "navigation": nav,
    }

    if dry_run:
        result["status"] = "dry_run_ok"
        result["would_write_bank_number_0based"] = target_bank_number - 1
        result["note"] = "Guard passed; no data written (dry_run). Re-run with dry_run=False to flash."
        return result

    upload = upload_current_bank_from_json(
        bank_json=bank_json,
        bank_number=target_bank_number - 1,
        output_port=out_name,
        input_port=in_name,
        timeout_ms=timeout_ms,
        include_expression_presets=include_expression_presets,
        include_bank_chunk=include_bank_chunk,
    )
    send_editor_upload_complete_signal(output_port=out_name)

    result["status"] = upload.get("status")
    result["chunks_sent"] = upload.get("chunks_sent")
    result["chunks_total"] = upload.get("chunks_total")
    result["committed"] = upload.get("committed")
    result["post_state"] = (
        "Flash committed. Controller is now in editor-session mode (probes + foot navigation locked). "
        "POWER-CYCLE the MC8 before flashing another bank or verifying."
    )
    return result


@mcp.tool()
def build_current_bank_backup_json(
    bank_json: str,
    bank_number: int = 0,
    profile_number: int = 0,
    model_id: int = MC8_PRO_MODEL_ID,
    pretty: bool = True,
) -> dict[str, Any]:
    """Build a draft current-bank backup JSON wrapper locally from a supported bank spec."""
    bank_spec = _normalize_supported_bank_spec(_parse_json_argument(bank_json, "bank_json"))
    backup = _build_current_bank_backup_data(
        bank_spec=bank_spec,
        bank_number=_validate_7bit_value(bank_number, "bank_number"),
        profile_number=_validate_7bit_value(profile_number, "profile_number"),
        model_id=_validate_7bit_value(model_id, "model_id"),
    )
    return {
        "status": "completed",
        "decoded": {
            "bank_name": bank_spec["bank_name"],
            "preset_count": len(bank_spec["presets"]),
            "kind": "current-bank-backup",
        },
        "backup_json": _dump_json(backup, pretty=pretty),
    }


@mcp.tool()
def build_all_banks_backup_json(
    banks_json: str,
    controller_data_json: str = "{}",
    pretty: bool = True,
) -> dict[str, Any]:
    """Build a draft all-banks backup JSON container locally, with optional controllerData content."""
    raw_banks = _parse_json_argument(banks_json, "banks_json")
    if not isinstance(raw_banks, list):
        raise ValueError("banks_json must decode to an array of bank specs or bank backup objects")
    controller_data = _parse_json_argument(controller_data_json, "controller_data_json")
    if not isinstance(controller_data, dict):
        raise ValueError("controller_data_json must decode to a JSON object")

    bank_wrappers = []
    bank_arrangements = []
    for index, raw_bank in enumerate(raw_banks):
        if not isinstance(raw_bank, dict):
            raise ValueError(f"banks_json[{index}] must be an object")
        if isinstance(raw_bank.get("bankData"), dict) and isinstance(raw_bank["bankData"].get("bank"), dict):
            bank_wrapper = raw_bank
        else:
            bank_spec = _normalize_supported_bank_spec(raw_bank)
            bank_wrapper = _build_current_bank_backup_data(
                bank_spec=bank_spec,
                bank_number=index,
                profile_number=0,
                model_id=MC8_PRO_MODEL_ID,
            )
        bank_wrappers.append(bank_wrapper["bankData"]["bank"])
        bank_arrangements.append(bank_wrapper["bankData"]["bankArrangement"])

    backup = {
        "bankData": {
            "banks": bank_wrappers,
            "bankArrangement": bank_arrangements,
        },
        "controllerData": controller_data,
    }

    return {
        "status": "completed",
        "decoded": {
            "bank_count": len(bank_wrappers),
            "has_controller_data": bool(controller_data),
            "kind": "all-banks-backup",
        },
        "backup_json": _dump_json(backup, pretty=pretty),
    }


def _editor_backup_stringify(data: Any) -> str:
    # Mirror JS JSON.stringify(data): compact separators, key order preserved, non-ASCII kept.
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def _editor_backup_java_hash(data: Any) -> int:
    # Editor calculateCheckSum-style integrity hash: Java String.hashCode of JSON.stringify(data).
    string = _editor_backup_stringify(data)
    h = 0
    for ch in string:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h - 0x100000000 if h >= 0x80000000 else h


def _editor_backup_message(template_empty: dict[str, Any], slot: int, channel: int,
                           t: int = 0, d0: int = 0, d1: int = 0) -> dict[str, Any]:
    msg = copy.deepcopy(template_empty)
    msg["m"] = slot
    msg["c"] = channel
    msg["t"] = t
    msg["a"] = 1 if t != 0 else 0
    data = [0] * len(msg["data"])
    if t != 0:
        data[0] = d0
        data[1] = d1
    msg["data"] = data
    return msg


def _editor_backup_msgarray(active: list[tuple[int, int, int]], slot_count: int,
                            template_empty: dict[str, Any], channel: int) -> list[dict[str, Any]]:
    arr: list[dict[str, Any]] = []
    for slot in range(slot_count):
        if slot < len(active):
            t, d0, d1 = active[slot]
            arr.append(_editor_backup_message(template_empty, slot, channel, t, d0, d1))
        else:
            arr.append(_editor_backup_message(template_empty, slot, channel))
    return arr


def _editor_backup_active_from_entry(entry: dict[str, Any]) -> list[tuple[int, int, int]]:
    # A layout page entry -> ordered editor JSON messages (t: 2=CC, 1=PC).
    if "cc0" in entry and "pc" in entry:
        return [
            (MESSAGE_TYPE_CC, 0, int(entry["cc0"])),   # CC0 bank-select MSB, value = bank
            (MESSAGE_TYPE_PC, int(entry["pc"]), 0),    # program change
        ]
    if "cc_number" in entry and "cc_value" in entry:
        return [(MESSAGE_TYPE_CC, int(entry["cc_number"]), int(entry["cc_value"]))]
    return []


@mcp.tool()
def build_editor_native_restore_file(
    base_backup_path: str,
    layout_json: str,
    output_path: str,
    midi_channel: int = 1,
) -> dict[str, Any]:
    """Generate an editor-IMPORTABLE all-banks backup file (native schema + valid hash).

    This is the only MCP path that yields a file the official Morningstar editor will restore to
    FLASH so it survives a power-cycle. (MCP MIDI writes via the 0x70 path are RAM-only, and the
    persistent group-7 upload protocol is served over the controller's USB-serial interface, not
    MIDI - see upload_current_bank_from_json.) It clones a real editor all-banks backup for schema,
    controller settings, preset field shape, and hash algorithm, then regenerates the banks named in
    layout_json in the editor's exact native encoding and recomputes the integrity hash.

    base_backup_path: path to a real editor all-banks backup JSON (dumpType allBanks, data.bankArray).
    layout_json: JSON array of layout bank objects (like axefx_factory_layout.json). Array index i
        maps to editor bank i+1. Each object: {bank_name, page_1:[{mc8_preset,cc0,pc,short_name,long_name}
        or {mc8_preset,cc_number,cc_value,...}], page_2:[...scene entries...]}. A null element leaves
        that bank unchanged from the base backup.
    output_path: where to write the importable backup file.
    """
    base = json.loads(Path(base_backup_path).read_text(encoding="utf-8"))
    if not (isinstance(base.get("data"), dict) and isinstance(base["data"].get("bankArray"), list)):
        raise ValueError("base_backup_path must be a real editor all-banks backup (data.bankArray)")
    if base.get("hash") != _editor_backup_java_hash(base["data"]):
        raise ValueError("base backup hash does not validate; not a clean editor backup")

    layout = _parse_json_argument(layout_json, "layout_json")
    if not isinstance(layout, list):
        raise ValueError("layout_json must decode to an array of layout bank objects")

    bank_array = base["data"]["bankArray"]
    template_preset = copy.deepcopy(bank_array[0]["presetArray"][0])
    slot_count = len(template_preset["msgArray"])
    empty_msg = copy.deepcopy(template_preset["msgArray"][2])
    empty_msg["t"] = 0
    empty_msg["a"] = 0
    empty_msg["data"] = [0] * len(empty_msg["data"])

    changed: list[int] = []
    for index, lb in enumerate(layout):
        if lb is None:
            continue
        if index >= len(bank_array):
            raise ValueError(f"layout index {index} exceeds base bankArray length {len(bank_array)}")
        bank = bank_array[index]
        if "bank_name" in lb or "bankName" in lb:
            bank["bankName"] = str(lb.get("bank_name") or lb.get("bankName"))
        presets = bank["presetArray"]
        page_1 = lb.get("page_1", []) or []
        page_2 = lb.get("page_2", []) or []

        for slot, entry in enumerate(page_1[:8]):
            p = presets[slot]
            p["shortName"] = str(entry.get("short_name", ""))
            p["longName"] = str(entry.get("long_name", entry.get("short_name", "")))
            p["toggleName"] = ""
            p["shiftName"] = ""
            p["msgArray"] = _editor_backup_msgarray(
                _editor_backup_active_from_entry(entry), slot_count, empty_msg, midi_channel)
        for offset, entry in enumerate(page_2[:8]):
            p = presets[8 + offset]
            p["shortName"] = str(entry.get("short_name", ""))
            p["longName"] = str(entry.get("long_name", entry.get("short_name", "")))
            p["toggleName"] = ""
            p["shiftName"] = ""
            p["msgArray"] = _editor_backup_msgarray(
                _editor_backup_active_from_entry(entry), slot_count, empty_msg, midi_channel)
        for slot in range(16, len(presets)):
            p = presets[slot]
            p["shortName"] = ""
            p["longName"] = ""
            p["toggleName"] = ""
            p["shiftName"] = ""
            p["msgArray"] = _editor_backup_msgarray([], slot_count, empty_msg, midi_channel)
        changed.append(index)

    base["hash"] = _editor_backup_java_hash(base["data"])
    base["description"] = "MCP-generated editor-native restore file"
    out_string = _editor_backup_stringify(base)
    Path(output_path).write_text(out_string, encoding="utf-8")

    reread = json.loads(Path(output_path).read_text(encoding="utf-8"))
    hash_valid = reread["hash"] == _editor_backup_java_hash(reread["data"])
    return {
        "status": "completed",
        "output_path": output_path,
        "hash_valid": hash_valid,
        "banks_regenerated": len(changed),
        "bank_index_range": [changed[0], changed[-1]] if changed else [],
        "decoded": {
            "kind": "editor-native-all-banks-restore",
            "importable_via": "official Morningstar editor -> Restore all banks (commits to flash)",
        },
    }


@mcp.tool()
def build_aux_controller_data_json(
    aux_config_json: str,
    pretty: bool = True,
) -> dict[str, Any]:
    """Build a draft controllerData payload for aux switch mappings."""
    raw_actions = _parse_json_argument(aux_config_json, "aux_config_json")
    if not isinstance(raw_actions, list):
        raise ValueError("aux_config_json must decode to an array of aux switch actions")

    controller_data = _build_draft_controller_data_from_aux_config(raw_actions)
    return _build_controller_data_tool_result(controller_data, pretty=pretty)


@mcp.tool()
def build_trs_aux_fixed_functions_controller_data_json(
    omniport: int,
    tip_function: str = "",
    ring_function: str = "",
    tip_ring_function: str = "",
    pretty: bool = True,
) -> dict[str, Any]:
    """Build a draft controllerData payload for one Omniport configured as a TRS aux switch with fixed functions."""
    if omniport < 1 or omniport > MC8_PRO_OMNIPORT_COUNT:
        raise ValueError(f"omniport must be in 1..{MC8_PRO_OMNIPORT_COUNT}")

    slot_specs = [
        ("tip", tip_function),
        ("ring", ring_function),
        ("tip+ring", tip_ring_function),
    ]
    aux_actions: list[dict[str, Any]] = []
    for slot_name, function_name in slot_specs:
        normalized_function = function_name.strip().lower()
        if not normalized_function:
            continue
        if normalized_function not in SUPPORTED_AUX_FIXED_FUNCTIONS:
            raise ValueError(
                "function must be one of: "
                + ", ".join(sorted(SUPPORTED_AUX_FIXED_FUNCTIONS))
            )
        aux_actions.append(
            {
                "omniport": omniport,
                "slot": slot_name,
                "kind": "fixed_function",
                "function": normalized_function,
            }
        )

    if not aux_actions:
        raise ValueError("At least one of tip_function, ring_function, or tip_ring_function must be set")

    controller_data = _build_draft_controller_data_from_aux_config(aux_actions)
    return _build_controller_data_tool_result(controller_data, pretty=pretty)


@mcp.tool()
def inspect_backup_json(
    backup_json: str,
) -> dict[str, Any]:
    """Inspect a Morningstar-style backup JSON blob and summarize its bank and controller-data structure."""
    payload = _parse_json_argument(backup_json, "backup_json")
    if not isinstance(payload, dict):
        raise ValueError("backup_json must decode to a JSON object")

    if isinstance(payload.get("bankData"), dict) and isinstance(payload["bankData"].get("bank"), dict):
        bank = payload["bankData"]["bank"]
        return {
            "status": "completed",
            "decoded": {
                "kind": "current-bank-backup",
                "bank_name": bank.get("bankName", ""),
                "bank_number": bank.get("bankNumber", 0),
                "profile_number": bank.get("profileNumber", 0),
                "preset_count": len(bank.get("presetArray", [])),
                "has_bank_arrangement": "bankArrangement" in payload["bankData"],
            },
        }

    if isinstance(payload.get("bankData"), dict):
        bank_data = payload["bankData"]
        banks = bank_data.get("banks", [])
        arrangements = bank_data.get("bankArrangement", [])
        bank_names = [bank.get("bankName", "") for bank in banks if isinstance(bank, dict)]
        controller_data = payload.get("controllerData")
        controller_aux_actions: list[dict[str, Any]] = []
        controller_aux_topologies: list[str] = []
        if isinstance(controller_data, dict):
            raw_controller_aux_actions, controller_aux_topologies = _extract_draft_controller_aux_actions(controller_data)
            for aux_action in raw_controller_aux_actions:
                controller_aux_actions.append(
                    {
                        "topology": aux_action.get("topology", ""),
                        "omniport": aux_action.get("omniport", 0),
                        "aux_switch": aux_action.get("auxSwitch", 0),
                        "slot": aux_action.get("slot", ""),
                        "kind": aux_action.get("kind", ""),
                        "summary": aux_action.get("function") or aux_action.get("ccNumber", 0),
                    }
                )
        return {
            "status": "completed",
            "decoded": {
                "kind": "all-banks-backup",
                "bank_count": len(banks),
                "bank_names": bank_names,
                "bank_arrangement_count": len(arrangements) if isinstance(arrangements, list) else 0,
                "has_controller_data": "controllerData" in payload,
                "controller_data_type": controller_data.get("type", "") if isinstance(controller_data, dict) else "",
                "controller_aux_topologies": controller_aux_topologies,
                "controller_aux_switch_count": len(controller_aux_actions),
                "controller_aux_actions": controller_aux_actions,
            },
        }

    raise ValueError("Unsupported backup_json wrapper")


def main() -> None:
    """Run the Morningstar MC8 Pro MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()