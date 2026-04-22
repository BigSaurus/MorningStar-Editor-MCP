import inspect
import json
import os
import time
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

ACTION_TYPE_PRESS = 0x01
TOGGLE_TYPE_POS_1 = 0x00
MESSAGE_TYPE_PC = 0x01
MESSAGE_TYPE_CC = 0x02
CONTROLLER_FUNCTION_BANK_UP = 0x00
CONTROLLER_FUNCTION_BANK_DOWN = 0x01
CONTROLLER_FUNCTION_TOGGLE_PAGE = 0x04
MAX_RAW_MESSAGE_PAYLOAD_SIZE = 64
MESSAGE_JSON_DATA_FIELD_COUNT = 18
MC8_PRO_PRESET_COUNT = 16

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
    "set_current_bank_name": {
        "group": "Name and UI Writes",
        "safety": "write",
        "verification": "live-verified",
        "transport": "request-response",
        "returns": "Returns the raw response plus a decoded echo of the target bank name and save mode.",
        "notes": [
            "save=False applies a temporary override that reverts on bank change.",
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
            "save=False applies a temporary override that reverts on bank change.",
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
            "save=False applies a temporary override that reverts on bank change.",
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
            "save=False applies a temporary override that reverts on bank change.",
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


def _is_morningstar_sysex(values: list[int]) -> bool:
    return (
        len(values) >= 18
        and values[0] == 0xF0
        and values[-1] == 0xF7
        and values[1:4] == MORNINGSTAR_MANUFACTURER_ID
        and values[6] == MORNINGSTAR_OPCODE_1
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
    if preset_number < 0 or preset_number >= MC8_PRO_PRESET_COUNT:
        raise ValueError(f"preset_number must be in 0..{MC8_PRO_PRESET_COUNT - 1}")
    return chr(ord("A") + preset_number)


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
        op4=_save_opcode(save),
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
            "preset": _preset_label_from_number(preset_number),
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
    for preset_number in range(MC8_PRO_PRESET_COUNT):
        preset_spec = preset_lookup.get(
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
        return {
            "status": "completed",
            "decoded": {
                "kind": "all-banks-backup",
                "bank_count": len(banks),
                "bank_names": bank_names,
                "bank_arrangement_count": len(arrangements) if isinstance(arrangements, list) else 0,
                "has_controller_data": "controllerData" in payload,
            },
        }

    raise ValueError("Unsupported backup_json wrapper")


def main() -> None:
    """Run the Morningstar MC8 Pro MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()