"""Some simple ports from sdlcntrl.cpp that are generally useful for dealing with controls"""
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

if TYPE_CHECKING:
    from desmume.emulator import DeSmuME


class Joy:
    JOY_AXIS = 0
    JOY_HAT = 1
    JOY_BUTTON = 2


class JoyHats:
    JOY_HAT_RIGHT = 0
    JOY_HAT_LEFT = 1
    JOY_HAT_UP = 2
    JOY_HAT_DOWN = 3


class Keys:
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

def add_key(keypad, key):
    return keypad | key


def rm_key(keypad, key):
    return keypad & ~key


def keymask(k):
    return 1 << k


def load_default_config() -> Tuple[List[int], List[int]]:
    """
    Returns the default (keyboard configuration),(joystick configuration).
    """
    return default_config_keyboard, default_config_joystick


def load_configured_config(emu: 'DeSmuME') -> Tuple[List[int], List[int]]:
    """
    Load the default for inputs.
    Also set's the default config for joystick in emulator.
    TODO: Support loading/saving from the DesMuME config file.
    """
    kbcfg, jscfg = load_default_config()

    for i, jskey in enumerate(jscfg):
        emu.input.joy_set_key(i, jskey)

    return kbcfg, jscfg
