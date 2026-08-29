# vim: ts=4:sw=4:expandtab

# This file is part of ReText (tkchan007/retext fork)
#
# Named, file-backed print layout presets (margins + print font), stored as
# one small JSON file per preset under a `print-presets` directory next to
# ReText's own settings file. Deliberately not stored in the main QSettings
# config: presets are meant to be added to freely over time, inspected or
# copied individually, and are unrelated to the app's own flat settings.
#
# Preset schema (all keys always present on anything returned by
# loadPreset/listPresets; missing keys in an on-disk file are filled with
# defaults so older presets keep working if the schema grows later):
#   name: str
#   unit: "in"                        (only unit supported for now)
#   marginTop/Bottom/Left/Right: float (in `unit`)
#   printFont: str                    (QFont.toString() descriptor, "" = no override)
#
# Page size is intentionally not part of this schema yet -- planned as a
# follow-up. When it's added, a preset missing "pageSize" should fall back
# to the app's current default paper size, so nothing here needs to change
# to stay compatible.

import json
import os
import sys
import uuid

from ReText import getSettingsFilePath

# Values equivalent to the hardcoded margins ReText used before presets
# existed (20mm, 20mm, 13mm, 20mm -- left, top, right, bottom), used
# whenever no preset is active.
DEFAULT_PRESET = {
    'name': '(Default margins)',
    'unit': 'in',
    'marginTop': 0.79,
    'marginBottom': 0.79,
    'marginLeft': 0.79,
    'marginRight': 0.51,
    'printFont': '',
}


def presetsDir():
    path = os.path.join(os.path.dirname(getSettingsFilePath()), 'print-presets')
    os.makedirs(path, exist_ok=True)
    return path


def _presetPath(presetId):
    return os.path.join(presetsDir(), presetId + '.json')


def _fillDefaults(data):
    filled = dict(DEFAULT_PRESET)
    filled.update(data)
    return filled


def listPresets():
    """ Returns a list of (presetId, name) tuples, sorted by name.
    Files that fail to parse are skipped (with a warning printed to
    stderr) rather than breaking the whole list.
    """
    result = []
    directory = presetsDir()
    for entry in os.listdir(directory):
        if not entry.endswith('.json'):
            continue
        presetId = entry[:-len('.json')]
        preset = loadPreset(presetId)
        if preset is not None:
            result.append((presetId, preset['name']))
    result.sort(key=lambda item: item[1].lower())
    return result


def loadPreset(presetId):
    try:
        with open(_presetPath(presetId), encoding='utf-8') as f:
            data = json.load(f)
        return _fillDefaults(data)
    except (OSError, ValueError) as ex:
        print(f'Failed to load print preset {presetId!r}: {ex}', file=sys.stderr)
        return None


def savePreset(presetId, data):
    with open(_presetPath(presetId), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def deletePreset(presetId):
    try:
        os.remove(_presetPath(presetId))
    except FileNotFoundError:
        pass


def newPresetId():
    return uuid.uuid4().hex[:12]
