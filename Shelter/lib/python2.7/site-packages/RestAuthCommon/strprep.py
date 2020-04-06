# -*- coding: utf-8 -*-
#
# This file is part of RestAuthCommon.
#
# RestAuthCommon is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# RestAuthCommon is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with RestAuthCommon. If
# not, see <http://www.gnu.org/licenses/>.

"""stringprep methods for RestAuth entities.

.. moduleauthor:: Mathias Ertl <mati@restauth.net>
"""

from __future__ import unicode_literals, absolute_import

import re

from unicodedata import ucd_3_2_0 as unicodedata

from RestAuthCommon.error import PreconditionFailed

check_pattern = re.compile(
    '['

    # C.1.2 Non-ASCII space characters
    '\u00A0'  # NO-BREAK SPACE
    '\u1680'  # OGHAM SPACE MARK
    '\u2000'  # EN QUAD
    '\u2001'  # EM QUAD
    '\u2002'  # EN SPACE
    '\u2003'  # EM SPACE
    '\u2004'  # THREE-PER-EM SPACE
    '\u2005'  # FOUR-PER-EM SPACE
    '\u2006'  # SIX-PER-EM SPACE
    '\u2007'  # FIGURE SPACE
    '\u2008'  # PUNCTUATION SPACE
    '\u2009'  # THIN SPACE
    '\u200A'  # HAIR SPACE
    '\u200B'  # ZERO WIDTH SPACE
    '\u202F'  # NARROW NO-BREAK SPACE
    '\u205F'  # MEDIUM MATHEMATICAL SPACE
    '\u3000'  # IDEOGRAPHIC SPACE

    # C.2.1 ASCII control characters
    '\u0000-\u001F'  # [CONTROL CHARACTERS]
    '\u007F'  # DELETE

    # C.2.2 Non-ASCII control characters
    '\u0080-\u009F'  # [CONTROL CHARACTERS]
    '\u06DD'  # ARABIC END OF AYAH
    '\u070F'  # SYRIAC ABBREVIATION MARK
    '\u180E'  # MONGOLIAN VOWEL SEPARATOR
    '\u200C'  # ZERO WIDTH NON-JOINER
    '\u200D'  # ZERO WIDTH JOINER
    '\u2028'  # LINE SEPARATOR
    '\u2029'  # PARAGRAPH SEPARATOR
    '\u2060'  # WORD JOINER
    '\u2061'  # FUNCTION APPLICATION
    '\u2062'  # INVISIBLE TIMES
    '\u2063'  # INVISIBLE SEPARATOR
    '\u206A-\u206F'  # [CONTROL CHARACTERS]
    '\uFEFF'  # ZERO WIDTH NO-BREAK SPACE
    '\uFFF9-\uFFFC'  # [CONTROL CHARACTERS]
    '\U0001D173-\U0001D17A'  # [MUSICAL CONTROL CHARACTERS]

    # C.3 Private use
    '\uE000-\uF8FF'  # [PRIVATE USE, PLANE 0]
    '\U000F0000-\U000FFFFD'  # [PRIVATE USE, PLANE 15]
    '\U00100000-\U0010FFFD'  # [PRIVATE USE, PLANE 16]

    # C.4 Non-character code points
    '\uFDD0-\uFDEF'  # [NONCHARACTER CODE POINTS]
    '\uFFFE-\uFFFF'  # [NONCHARACTER CODE POINTS]
    '\U0001FFFE-\U0001FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0002FFFE-\U0002FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0003FFFE-\U0003FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0004FFFE-\U0004FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0005FFFE-\U0005FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0006FFFE-\U0006FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0007FFFE-\U0007FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0008FFFE-\U0008FFFF'  # [NONCHARACTER CODE POINTS]
    '\U0009FFFE-\U0009FFFF'  # [NONCHARACTER CODE POINTS]
    '\U000AFFFE-\U000AFFFF'  # [NONCHARACTER CODE POINTS]
    '\U000BFFFE-\U000BFFFF'  # [NONCHARACTER CODE POINTS]
    '\U000CFFFE-\U000CFFFF'  # [NONCHARACTER CODE POINTS]
    '\U000DFFFE-\U000DFFFF'  # [NONCHARACTER CODE POINTS]
    '\U000EFFFE-\U000EFFFF'  # [NONCHARACTER CODE POINTS]
    '\U000FFFFE-\U000FFFFF'  # [NONCHARACTER CODE POINTS]
    '\U0010FFFE-\U0010FFFF'  # [NONCHARACTER CODE POINTS]

    # C.5 Surrogate codes
    '\uD800-\uDFFF'  # [SURROGATE CODES]

    # C.6 Inappropriate for plain text
    '\uFFF9'  # INTERLINEAR ANNOTATION ANCHOR
    '\uFFFA'  # INTERLINEAR ANNOTATION SEPARATOR
    '\uFFFB'  # INTERLINEAR ANNOTATION TERMINATOR
    '\uFFFC'  # OBJECT REPLACEMENT CHARACTER
    '\uFFFD'  # REPLACEMENT CHARACTER

    # C.7 Inappropriate for canonical representation
    '\u2FF0-\u2FFB'  # [IDEOGRAPHIC DESCRIPTION CHARACTERS]

    # C.8 Change display properties or are deprecated
    '\u0340'  # COMBINING GRAVE TONE MARK
    '\u0341'  # COMBINING ACUTE TONE MARK
    '\u200E'  # LEFT-TO-RIGHT MARK
    '\u200F'  # RIGHT-TO-LEFT MARK
    '\u202A'  # LEFT-TO-RIGHT EMBEDDING
    '\u202B'  # RIGHT-TO-LEFT EMBEDDING
    '\u202C'  # POP DIRECTIONAL FORMATTING
    '\u202D'  # LEFT-TO-RIGHT OVERRIDE
    '\u202E'  # RIGHT-TO-LEFT OVERRIDE
    '\u206A'  # INHIBIT SYMMETRIC SWAPPING
    '\u206B'  # ACTIVATE SYMMETRIC SWAPPING
    '\u206C'  # INHIBIT ARABIC FORM SHAPING
    '\u206D'  # ACTIVATE ARABIC FORM SHAPING
    '\u206E'  # NATIONAL DIGIT SHAPES
    '\u206F'  # NOMINAL DIGIT SHAPES

    # C.9 Tagging characters
    '\U000E0001'  # LANGUAGE TAG
    '\U000E0020-\U000E007F'  # [TAGGING CHARACTERS]
    ']'
)

# Table B.1 Commonly mapped to nothing:
prep_pattern = re.compile(
    '[\u00AD\u034F\u1806\u180B\u180C\u180D\u200B\u200C\u200D\u2060\uFE00\uFE01\uFE02\uFE03\uFE04'
    '\uFE05\uFE06\uFE07\uFE08\uFE09\uFE0A\uFE0B\uFE0C\uFE0D\uFE0E\uFE0F\uFEFF]')


def stringprep(name):
    """Lowercase, normalize and remove stringprep B.1 characters."""
    return prep_pattern.sub('', unicodedata.normalize('NFC', name)).lower()


def stringcheck(name):
    """Same as :py:func:`stringprep` but raises PreconditionFailed if name contains invalid characters."""
    name = prep_pattern.sub('', name)

    if check_pattern.search(name) is None:
        return unicodedata.normalize('NFC', name).lower()
    raise PreconditionFailed("Invalid characters")
