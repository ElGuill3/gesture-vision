"""Optional Windows virtual-gamepad adapter."""

import sys


_BUTTON_NAMES = (
    "XUSB_GAMEPAD_DPAD_UP", "XUSB_GAMEPAD_DPAD_DOWN", "XUSB_GAMEPAD_DPAD_LEFT", "XUSB_GAMEPAD_DPAD_RIGHT",
    "XUSB_GAMEPAD_A", "XUSB_GAMEPAD_B", "XUSB_GAMEPAD_X", "XUSB_GAMEPAD_Y",
    "XUSB_GAMEPAD_LEFT_SHOULDER", "XUSB_GAMEPAD_RIGHT_SHOULDER",
)
_SHOULDERS = {"XUSB_GAMEPAD_LEFT_SHOULDER": "LB", "XUSB_GAMEPAD_RIGHT_SHOULDER": "RB"}
_TRIGGERS = {"left_trigger": "LT", "right_trigger": "RT"}


def _settings(config):
    settings = config.get("GAMEPAD")
    if not isinstance(settings, dict):
        raise ValueError("GAMEPAD configuration is required")
    value = settings.get("trigger_value", 255)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError("GAMEPAD trigger_value must be an integer from 0 to 255")
    mapping = settings.get("hand_mapping", {})
    if not isinstance(mapping, dict):
        raise ValueError("GAMEPAD hand_mapping must be a mapping")
    for hand in ("left", "right"):
        controls = mapping.get(f"{hand}_hand", {}).get("controls", ())
        if isinstance(controls, str) or not isinstance(controls, (list, tuple)):
            raise ValueError("GAMEPAD hand_mapping controls must be a list")
    return settings


class GamepadAdapter:
    """Apply configured gestures to one virtual gamepad safely."""

    def __init__(self, pad, vg, settings):
        self.pad = pad
        self.settings = settings
        self.buttons = {name: getattr(vg.XUSB_BUTTON, name) for name in _BUTTON_NAMES}
        mapping = settings.get("hand_mapping", {})
        self.controls = {hand: set(mapping.get(f"{hand}_hand", {}).get("controls", ())) for hand in ("left", "right")}

    def neutralize(self):
        """Release every supported control; repeat calls leave the pad neutral."""
        for button in self.buttons.values():
            self.pad.release_button(button)
        self.pad.left_trigger(value=0)
        self.pad.right_trigger(value=0)
        self.pad.update()

    def _controls_for(self, hand, label):
        controls, settings, buttons = self.controls[hand], self.settings, []
        if "dpad" in controls:
            for name in str(settings.get("gesture_to_dpad", {}).get(label) or "").split(","):
                button = self.buttons.get(name.strip())
                if button is not None:
                    buttons.append(button)
        action = settings.get("gesture_to_action_buttons", {}).get(label)
        if isinstance(action, str) and action.rsplit("_", 1)[-1] in controls and action in self.buttons:
            buttons.append(self.buttons[action])
        shoulder = settings.get("gesture_to_shoulder_buttons", {}).get(label)
        if shoulder in _SHOULDERS and _SHOULDERS[shoulder] in controls:
            buttons.append(self.buttons[shoulder])
        triggers = {name: 0 for name in _TRIGGERS}
        trigger = settings.get("gesture_to_triggers", {}).get(label)
        if trigger in _TRIGGERS and _TRIGGERS[trigger] in controls:
            triggers[trigger] = settings["trigger_value"]
        return buttons, triggers

    def apply(self, outcomes):
        """Replace this cycle's state, leaving invalid outcomes neutral."""
        self.neutralize()
        try:
            buttons, triggers = [], {name: 0 for name in _TRIGGERS}
            for hand in ("left", "right"):
                outcome = outcomes.get(hand, (None, 0.0)) if isinstance(outcomes, dict) else (None, 0.0)
                label = outcome[0] if isinstance(outcome, tuple) and outcome else None
                if not isinstance(label, str):
                    continue
                selected, values = self._controls_for(hand, label)
                buttons.extend(button for button in selected if button not in buttons)
                triggers.update({name: value for name, value in values.items() if value})
            for button in buttons:
                self.pad.press_button(button)
            self.pad.left_trigger(value=triggers["left_trigger"])
            self.pad.right_trigger(value=triggers["right_trigger"])
            self.pad.update()
        except BaseException:
            self.neutralize()
            raise


def open_gamepad(config):
    """Validate settings, then create a Windows-only optional device."""
    settings = _settings(config)
    if sys.platform != "win32":
        raise RuntimeError("The gamepad command is supported only on Windows")
    try:
        import vgamepad as vg
    except ImportError as error:
        raise RuntimeError("Install gesture-vision[gamepad] to use the gamepad command") from error
    return GamepadAdapter(vg.VX360Gamepad(), vg, settings)
