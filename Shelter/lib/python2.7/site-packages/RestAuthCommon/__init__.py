# This file is part of RestAuthCommon.
#
# RestAuthCommon is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# RestAuthCommon is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with RestAuthCommon. If
# not, see <http://www.gnu.org/licenses/>.

"""A collection of functions used in both server and client reference implementations.

.. moduleauthor:: Mathias Ertl <mati@restauth.net>
"""

from __future__ import unicode_literals, absolute_import
import warnings

import sys
import stringprep

PY2 = sys.version_info[0] == 2


def resource_validator(name):
    """Check the *name* of a resource for some really bad characters that shouldn't be used
    anywhere in RestAuth.

    This filters names containing a slash ("/") or colon (":") and those starting with '.'. It also
    filters control characters etc., including those from unicode.

    .. deprecated:: 0.7.0
       This method is deprecated in favour of the RestAuthCommon.strprep. This method will be
       removed in 0.7.1.

    :param str name: The name to validate
    :returns: False if the name contains any invalid characters, True otherwise.
    :rtype: bool
    """
    warnings.warn('This method is deprecated, use RestAuthCommon.strprep.stringcheck() instead.',
                  DeprecationWarning)

    if PY2 and isinstance(name, str):  # pragma: py2
        name = name.decode('utf-8')

    # filter various dangerous characters
    for enc_char in name:
        if stringprep.in_table_c12(enc_char):  # C.1.2 Non-ASCII space characters
            return False
        if stringprep.in_table_c21_c22(enc_char):  # C.2 Control characters
            return False
        if stringprep.in_table_c3(enc_char):  # C.3 Private use
            return False
        if stringprep.in_table_c4(enc_char):  # C.4 Non-character code points
            return False
        if stringprep.in_table_c5(enc_char):  # C.5 Surrogate codes
            return False
        if stringprep.in_table_c6(enc_char):  # C.6 Inappropriate for plain text
            return False
        if stringprep.in_table_c7(enc_char):  # C.7 Inappropriate for canonical representation
            return False
        if stringprep.in_table_c8(enc_char):  # C.8 Change display properties or are deprecated
            return False
        if stringprep.in_table_c9(enc_char):  # C.9 Tagging characters
            return False

    return True
