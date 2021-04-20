# Copyright 2016-2020 Alex Yatskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os

import anki
import anki.sync
import aqt
import enum

#
# Utilities
#
def setting(key):
    defaults = {
        "noteTypes": ["japanese"],
        "srcFields": ["Expression", "Kanji"],
        "KanjiLearnedByDayjplpt5": 0,
        "KanjiLearnedByDayjplpt4": 0,
        "KanjiLearnedByDayjplpt3": 0,
        "KanjiLearnedByDayjplpt2": 0,
        "KanjiLearnedByDayjplpt1": 0
    }

    try:
        return aqt.mw.addonManager.getConfig(__name__).get(key, defaults[key])
    except:
        raise Exception('setting {} not found'.format(key))
