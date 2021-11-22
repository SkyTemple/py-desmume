"""
Some simple ports from sdlcntrl.cpp that are generally useful for dealing with controls.

Some of this only applies if used with GTK (eg. the keyboard configuration), other things
apply generally, such as the joystick configuration.
"""
#  Copyright 2020 Marco Köpcke (Parakoopa)
# 
#  This file is part of py-desmume.
# 
#  py-desmume is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  py-desmume is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with py-desmume.  If not, see <https://www.gnu.org/licenses/>.
from typing import Tuple, List, TYPE_CHECKING
from desmume.i18n_util import _


if TYPE_CHECKING:
    from desmume.emulator import DeSmuME


class Joy:
    """Joystick input types."""
    JOY_AXIS = 0
    JOY_HAT = 1
    JOY_BUTTON = 2


class JoyHats:
    """Jostick hat identifiers."""
    JOY_HAT_RIGHT = 0
    JOY_HAT_LEFT = 1
    JOY_HAT_UP = 2
    JOY_HAT_DOWN = 3


class Keys:
    """DS key identifiers. NB_KEYS contains the total number of keys."""
    NB_KEYS	= 15
    KEY_NONE = 0
    KEY_A = 1
    KEY_B = 2
    KEY_SELECT = 3
    KEY_START = 4
    KEY_RIGHT = 5
    KEY_LEFT = 6
    KEY_UP = 7
    KEY_DOWN = 8
    KEY_R = 9
    KEY_L = 10
    KEY_X = 11
    KEY_Y = 12
    KEY_DEBUG = 13
    KEY_BOOST = 14
    KEY_LID = 15
    NO_KEY_SET = 0xFFFF


# Indices are emulator keys (see above), starting with KEY_A.
# Values are Gdk key codes and SDL joystick codes respectively.
# Keys.NO_KEY_SET is a magic number for no key set (sint16 -1)
default_config_keyboard = [
    120, 122, 65506, 65293, 65363, 65361, 65362, 65364, 119, 113, 115, 97, 112, 111, 65288
]
default_config_joystick = [
    513, 512, 517, 520, 1, 0, 2, 3, 519, 518, 516, 515, Keys.NO_KEY_SET, Keys.NO_KEY_SET, 514
]

key_names = [
    "A", "B", "Select", "Start",
    "Right", "Left", "Up", "Down",
    "R", "L", "X", "Y",
    "Debug", "Boost",
    "Lid"
]


key_names_localized = [
    _("A"),  # TRANSLATORS: DS Key name
    _("B"),  # TRANSLATORS: DS Key name
    _("Select"),  # TRANSLATORS: DS Key name
    _("Start"),  # TRANSLATORS: DS Key name
    _("Right"),  # TRANSLATORS: DS Key name
    _("Left"),  # TRANSLATORS: DS Key name
    _("Up"),  # TRANSLATORS: DS Key name
    _("Down"),  # TRANSLATORS: DS Key name
    _("R"),  # TRANSLATORS: DS Key name
    _("L"),  # TRANSLATORS: DS Key name
    _("X"),  # TRANSLATORS: DS Key name
    _("Y"),  # TRANSLATORS: DS Key name
    _("Debug"),  # TRANSLATORS: DS Key name
    _("Boost"),  # TRANSLATORS: DS Key name
    _("Lid")  # TRANSLATORS: DS Key name
]


def add_key(keypad, key):
    """
    Add a key to a keypad -> press the key. ``key`` is the keymask returned by ``keymask``.

    You don't need to call this manually, see
    :func:`~desmume.module.emulator.DeSmuME_Input.keypad_add_key` instead.
    """
    return keypad | key


def rm_key(keypad, key):
    """
    Remove a key from a keypad -> release the key. ``key`` is the keymask returned by ``keymask``.

    You don't need to call this manually, see
    :func:`~desmume.module.emulator.DeSmuME_Input.keypad_rm_key` instead.
    """
    return keypad & ~key


def keymask(k):
    """Returns the keymask for key ``k``. ``k`` is a constant of the ``Keys`` class."""
    return 1 << (k - 1) if k > 0 else 0


def load_default_config() -> Tuple[List[int], List[int]]:
    """
    Returns the default (keyboard configuration),(joystick configuration).

    The keyboard configuration is Gdk key IDs.
    """
    return default_config_keyboard, default_config_joystick


def load_configured_config(emu: 'DeSmuME') -> Tuple[List[int], List[int]]:
    """
    Load the default for inputs.
    Also set's the default config for joystick in emulator.

    The keyboard configuration is Gdk key IDs.

    :todo: Support loading/saving from the DesMuME config file.
    """
    kbcfg, jscfg = load_default_config()

    for i, jskey in enumerate(jscfg):
        emu.input.joy_set_key(i, jskey)

    return kbcfg, jscfg
