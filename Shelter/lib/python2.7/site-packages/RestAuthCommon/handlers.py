# -*- coding: utf-8 -*-
#
# This file is part of RestAuthCommon (https://common.restauth.net).
#
# RestAuthCommon is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# RestAuthCommon is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with RestAuthCommon. If
# not, see <http://www.gnu.org/licenses/>.

"""Classes and methods related to content handling.

.. moduleauthor:: Mathias Ertl <mati@restauth.net>
"""

from __future__ import unicode_literals

import sys

from RestAuthCommon import error

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:  # pragma: py2
    string_types = basestring
else:  # pragma: py3
    string_types = (str, bytes, )


class ContentHandler(object):
    """A common base class for all content handlers.

    If you want to implement your own content handler, you must subclass this class and implement
    all marshal_* and unmarshal_* methods.

    **Never use this class directly.** It does not marshal or unmarshal any content itself.

    Any keyword arguments will be set as instance attributes. This means that you can instantiate
    a handler with different settings, for example, this would instantiate a
    :py:class:`PickleContentHandler`, that uses pickle protocol version 1:

        >>> h = PickleContentHandler().PROTOCOL
        2
        >>> PickleContentHandler(PROTOCOL=1).PROTOCOL
        1
    """

    mime = None
    """Override this with the MIME type handled by your handler."""

    librarypath = None
    """Override ``librarypath`` to lazily load named library upon first use.

    This may be a toplevel module (e.g. ``"json"``) or a submodule (e.g.  ``"lxml.etree"``). The
    named library is accessable via ``self.library``.

    Example::

        class XMLContentHandler(ContentHandler):
            librarypath = 'lxml.etree'

            def unmarshal_str(self, data):
                tree = self.library.Element(data)
                # ...
    """

    SUPPORT_NESTED_DICTS = True
    """Set to False if your content handler does not support nested dictionaries as used e.g.
    during user-creation."""

    _library = None

    @property
    def library(self):
        """Library configured with the ``librarypath`` class variable."""
        if self._library is None:
            if '.' in self.librarypath:
                mod, lib = self.librarypath.rsplit('.', 1)
                _temp = __import__(mod, fromlist=[str(lib)])
                self._library = getattr(_temp, lib)
            else:
                self._library = __import__(self.librarypath)
        return self._library

    def __init__(self, **kwargs):
        for k, w in kwargs.items():
            setattr(self, k, w)

    def _normalize_list3(self, l):  # pragma: py3
        """Converts any byte objects of l to str objects."""
        return [e.decode('utf-8') if isinstance(e, bytes) else e for e in l]

    def _normalize_list2(self, l):  # pragma: py2
        """Converts any str objects of l to unicode objects."""
        return [e.decode('utf-8') if isinstance(e, str) else e for e in l]

    def _normalize_dict3(self, d):  # pragma: py3
        """Converts any keys or values of d that are bytes to str."""
        def conv(v):
            if isinstance(v, bytes):
                return v.decode('utf-8')
            elif isinstance(v, list):
                return self._normalize_list3(v)
            elif isinstance(v, dict):
                return self._normalize_dict3(v)
            return v

        return {conv(k): conv(v) for k, v in d.items()}

    def _normalize_dict2(self, d):  # pragma: py2
        """Converts any keys or values of d that are str to unicode."""
        def conv(v):
            if isinstance(v, str):
                return v.decode('utf-8')
            elif isinstance(v, list):
                return self._normalize_list2(v)
            elif isinstance(v, dict):
                return self._normalize_dict2(v)
            return v

        return {conv(k): conv(v) for k, v in d.iteritems()}

    def _normalize_str3(self, s):  # pragma: py3
        """Converts byte objects to str."""
        return s.decode('utf-8') if isinstance(s, bytes) else s

    def _normalize_str2(self, s):  # pragma: py2
        """Converts str objects to unicode."""
        return s.decode('utf-8') if isinstance(s, str) else s

    def marshal(self, obj):
        """Shortcut for marshalling just any object.

        .. NOTE:: If you know the type of **obj** in advance, you should use the marshal_* methods
            directly for improved speed.

        :param obj: The object to marshall.
        :return: The marshalled representation of the object.
        :rtype: str
        :raise error.MarshalError: If marshalling goes wrong in any way.
        """
        if isinstance(obj, string_types):
            func_name = 'marshal_str'
        else:
            func_name = 'marshal_%s' % (obj.__class__.__name__)

        try:
            func = getattr(self, func_name)
            return func(obj)
        except error.MarshalError as e:
            raise
        except Exception as e:
            raise error.MarshalError(e)

    def unmarshal_str(self, data):  # pragma: no cover
        """Unmarshal a string.

        :param data: Data to unmarshal.
        :type  data: bytes in python3, str in python2
        :rtype: str in python3, unicode in python2
        """
        pass

    def unmarshal_dict(self, body):  # pragma: no cover
        """Unmarshal a dictionary.

        :param data: Data to unmarshal.
        :type  data: bytes in python3, str in python2
        :rtype: dict
        """
        pass

    def unmarshal_list(self, body):  # pragma: no cover
        """Unmarshal a list.

        :param data: Data to unmarshal.
        :type  data: bytes in python3, str in python2
        :rtype: list
        """
        pass

    def marshal_str(self, obj):  # pragma: no cover
        """Marshal a string.

        :param obj: Data to marshal.
        :type  obj: str, bytes, unicode
        :rtype: bytes in python3, str in python2
        """
        pass

    def marshal_list(self, obj):  # pragma: no cover
        """Marshal a list.

        :param obj: Data to marshal.
        :type  obj: list
        :rtype: bytes in python3, str in python2
        """
        pass

    def marshal_dict(self, obj):  # pragma: no cover
        """Marshal a dictionary.

        :param obj: Data to marshal.
        :type  obj: dict
        :rtype: bytes in python3, str in python2
        """
        pass

    if PY3:  # pragma: py3
        normalize_str = _normalize_str3
        normalize_list = _normalize_list3
        normalize_dict = _normalize_dict3
    else:  # pragma: py2
        normalize_str = _normalize_str2
        normalize_list = _normalize_list2
        normalize_dict = _normalize_dict2


class JSONContentHandler(ContentHandler):
    """Handler for JSON encoded content.

    .. seealso:: `Specification <http://www.json.org>`_, `WikiPedia
       <http://en.wikipedia.org/wiki/JSON>`_
    """

    librarypath = 'json'
    mime = 'application/json'
    """The mime-type used by this content handler is 'application/json'."""

    SEPARATORS = (str(','), str(':'))

    def __init__(self, **kwargs):
        super(JSONContentHandler, self).__init__(**kwargs)

        if PY3:  # pragma: py3
            class ByteEncoder(self.library.JSONEncoder):
                def decode_dict(self, d):
                    def key(v):  # keys are not handled by self.default()
                        if isinstance(v, bytes):
                            return v.decode('utf-8')
                        return v

                    def val(v):  # handle nested dicts
                        if isinstance(v, dict):
                            return self.decode_dict(v)
                        return v

                    return {key(k): val(v) for k, v in d.items()}

                def encode(self, obj):
                    if isinstance(obj, dict):
                        obj = self.decode_dict(obj)

                    return super(ByteEncoder, self).encode(obj)

                def default(self, obj):  # for objects of unknown type (i.e. bytes)
                    if isinstance(obj, bytes):
                        return obj.decode('utf-8')
                    return super(ByteEncoder, self).default(obj)

            self.encoder = ByteEncoder
        else:  # pragma: py2
            self.encoder = self.library.JSONEncoder

    def unmarshal_str(self, body):
        try:
            pure = self.library.loads(self.normalize_str(body))
            if not isinstance(pure, list) or len(pure) != 1:
                raise error.UnmarshalError("Could not parse body as string")

            string = pure[0]

            # In python 2.7.1 (not 2.7.2) json.loads("") returns a str and not unicode.
            return self.normalize_str(string)
        except ValueError as e:
            raise error.UnmarshalError(e)

    def unmarshal_dict(self, body):
        try:
            return self.library.loads(self.normalize_str(body))
        except ValueError as e:
            raise error.UnmarshalError(e)

    def unmarshal_list(self, body):
        try:
            return self.library.loads(self.normalize_str(body))
        except ValueError as e:
            raise error.UnmarshalError(e)

    def marshal_str(self, obj):
        try:
            dumped = self.library.dumps([obj], separators=self.SEPARATORS, cls=self.encoder)
            return dumped.encode('utf-8')
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_list(self, obj):
        try:
            dumped = self.library.dumps(obj, separators=self.SEPARATORS, cls=self.encoder)
            return dumped.encode('utf-8')
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_dict(self, obj):
        try:
            dumped = self.library.dumps(obj, separators=self.SEPARATORS, cls=self.encoder)
            return dumped.encode('utf-8')
        except Exception as e:
            raise error.MarshalError(e)


class BSONContentHandler(ContentHandler):
    """Handler for BSON ("Binary JSON") encoded content.

    .. NOTE:: This contant handler requires either the ``pymongo`` or the ``bson`` library to be
       installed.

    .. seealso:: `Specification <http://bsonspec.org/>`_, `WikiPedia
       <http://en.wikipedia.org/wiki/BSON>`_,
       `pymongo <https://pypi.python.org/pypi/pymongo>`_ on PyPi,
       `bson <https://pypi.python.org/pypi/bson>`_ on PyPi
    """
    mime = 'application/bson'
    """The mime-type used by this content handler is 'application/json'."""

    librarypath = 'bson'

    def __init__(self, **kwargs):
        super(BSONContentHandler, self).__init__(**kwargs)

        if hasattr(self.library, 'BSON'):  # pragma: pymongo
            self.dumps = self.library.BSON.encode
            self.loads = lambda d: self.library.BSON(d).decode()
        else:  # pragma: libbson
            self.dumps = self.library.dumps
            self.loads = self.library.loads

    def marshal_dict(self, obj):
        try:
            return self.marshal_cast(self.dumps({'d': self.normalize_dict(obj), }))
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_list(self, obj):
        try:
            return self.marshal_cast(self.dumps({'l': self.normalize_list(obj), }))
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_str(self, obj):
        try:
            return self.marshal_cast(self.dumps({'s': self.normalize_str(obj), }))
        except Exception as e:
            raise error.MarshalError(e)

    def _unmarshal_dict2(self, body):  # pragma: py2
        # NOTE: We convert unicode because some old versions of RestAuthClient
        #       pass unicode and bson can't handle it.
        if isinstance(body, unicode):  # pragma: no cover
            body = body.encode('utf-8')
        return self.loads(body)['d']

    def _unmarshal_list2(self, body):  # pragma: py2
        if isinstance(body, unicode):  # pragma: no cover
            body = body.encode('utf-8')
        return self.loads(body)['l']

    def _unmarshal_str2(self, body):  # pragma: py2
        if isinstance(body, unicode):  # pragma: no cover
            body = body.encode('utf-8')
        return self.loads(body)['s']

    def _unmarshal_dict3(self, body):  # pragma: py3
        return self.loads(body)['d']

    def _unmarshal_list3(self, body):  # pragma: py3
        return self.loads(body)['l']

    def _unmarshal_str3(self, body):  # pragma: py3
        return self.loads(body)['s']

    if PY3:  # pragma: py3
        unmarshal_dict = _unmarshal_dict3
        unmarshal_list = _unmarshal_list3
        unmarshal_str = _unmarshal_str3
        marshal_cast = bytes
    else:  # pragma: py2
        unmarshal_dict = _unmarshal_dict2
        unmarshal_list = _unmarshal_list2
        unmarshal_str = _unmarshal_str2
        marshal_cast = str


class MessagePackContentHandler(ContentHandler):
    """Handler for MessagePack encoded content.

    .. NOTE:: This content handler requires the ``msgpack-python`` library to be installed.

    .. seealso:: `Specification <http://msgpack.org/>`_, `WikiPedia
       <http://en.wikipedia.org/wiki/MessagePack>`_, `msgpack-python
       <https://pypi.python.org/pypi/msgpack-python/>`_ on PyPI.
    """
    mime = 'application/messagepack'
    """The mime-type used by this content handler is 'application/messagepack'."""

    librarypath = 'msgpack'

    def marshal_dict(self, obj):
        try:
            return self.library.packb(self.normalize_dict(obj))
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_list(self, obj):
        try:
            return self.library.packb(self.normalize_list(obj))
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_str(self, obj):
        try:
            return self.library.packb(self.normalize_str(obj))
        except Exception as e:
            raise error.MarshalError(e)

    def unmarshal_dict(self, body):
        return self.normalize_dict(self.library.unpackb(body))

    def unmarshal_list(self, body):
        return self.normalize_list(self.library.unpackb(body))

    def unmarshal_str(self, body):
        return self.normalize_str(self.library.unpackb(body))


class FormContentHandler(ContentHandler):
    """Handler for HTML Form urlencoded content.

    .. WARNING:: Because of the limitations of urlencoded forms, this handler does not support
       nested dictionaries. The primary use of this content handler is to enable you to manually
       add data with e.g. the curl command line utility, where you don't want to serialize posted
       data manually. Do not use this class in production.
    """

    mime = 'application/x-www-form-urlencoded'
    """The mime-type used by this content handler is 'application/x-www-form-urlencoded'."""

    SUPPORT_NESTED_DICTS = False

    def __init__(self, **kwargs):
        super(FormContentHandler, self).__init__(**kwargs)

        if PY2:  # pragma: py2
            from urlparse import parse_qs
            from urllib import urlencode
        else:  # pragma: py3
            from urllib.parse import parse_qs
            from urllib.parse import urlencode

        self.parse_qs = parse_qs
        self.urlencode = urlencode

    def _decode_dict(self, d):  # pragma: py2
        decoded = {}
        for key, value in d.items():
            key = key.decode('utf-8')
            if isinstance(value, (str, unicode)):
                decoded[key] = value.decode('utf-8')
            elif isinstance(value, list):  # pragma: no cover
                decoded[key] = [e.decode('utf-8') for e in value]
            elif isinstance(value, dict):  # pragma: no cover
                decoded[key] = self._decode_dict(value)

        return decoded

    def _normalize_str2(self, s):  # pragma: py2
        return s.encode('utf-8') if isinstance(s, unicode) else s

    def _normalize_list2(self, l):  # pragma: py2
        return [self._normalize_str2(s) for s in l]

    def _normalize_dict2(self, d):  # pragma: py2
        return {self._normalize_str2(k): self._normalize_str2(v) for k, v in d.iteritems()}

    def unmarshal_dict(self, body):
        if PY3:  # pragma: no branch py3
            body = body.decode('utf-8')

        parsed_dict = self.parse_qs(body, True)
        ret_dict = {}
        for key, value in parsed_dict.items():
            ret_dict[key] = value[0]

        if PY2:  # pragma: no branch py2
            ret_dict = self._decode_dict(ret_dict)

        return ret_dict

    def unmarshal_list(self, body):
        if PY3:  # pragma: no branch py3
            body = body.decode('utf-8')

        if body == '':
            return []

        parsed = self.parse_qs(body, True)['list']

        if PY2:  # pragma: no branch py2
            parsed = [e.decode('utf-8') for e in parsed]
        return parsed

    def unmarshal_str(self, body):
        if PY3:  # pragma: no branch py3
            body = body.decode('utf-8')

        parsed = self.parse_qs(body, True)['str'][0]
        return self.normalize_str(parsed)

    def marshal_str(self, obj):
        try:
            if PY2:  # pragma: py2
                obj = self._normalize_str2(obj)
                return self.urlencode({'str': obj})
            else:  # pragma: py3
                return self.urlencode({'str': obj}).encode('utf-8')
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_dict(self, obj):
        try:
            if PY2:  # pragma: no branch py2
                obj = self._normalize_dict2(obj)

            for value in obj.values():
                if isinstance(value, (list, dict)):
                    raise error.MarshalError("No nested dictionaries!")

            if PY3:  # pragma: py3
                return self.urlencode(obj, doseq=True).encode('utf-8')
            else:  # pragma: py2
                return self.urlencode(obj, doseq=True)
        except error.MarshalError:
            raise
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_list(self, obj):
        try:
            if PY2:  # pragma: py2
                obj = self._normalize_list2(obj)
                return self.urlencode({'list': obj}, doseq=True)
            else:  # pragma: py3
                return self.urlencode({'list': obj}, doseq=True).encode('utf-8')
        except Exception as e:
            raise error.MarshalError(e)


class PickleContentHandler(ContentHandler):
    """Handler for pickle-encoded content.

    .. seealso:: `module documentation
       <http://docs.python.org/2/library/pickle.html>`_,
       `WikiPedia <http://en.wikipedia.org/wiki/Pickle_(Python)>`_
    """

    mime = 'application/pickle'
    """The mime-type used by this content handler is 'application/pickle'."""

    librarypath = 'pickle'
    PROTOCOL = 2

    def marshal_str(self, obj):
        try:
            return self.library.dumps(self.normalize_str(obj), protocol=self.PROTOCOL)
        except Exception as e:
            raise error.MarshalError(str(e))

    def marshal_dict(self, obj):
        try:
            return self.library.dumps(self.normalize_dict(obj), protocol=self.PROTOCOL)
        except Exception as e:
            raise error.MarshalError(str(e))

    def marshal_list(self, obj):
        try:
            return self.library.dumps(self.normalize_list(obj), protocol=self.PROTOCOL)
        except Exception as e:
            raise error.MarshalError(str(e))

    def unmarshal_str(self, data):
        try:
            return self.normalize_str(self.library.loads(data))
        except Exception as e:
            raise error.UnmarshalError(str(e))

    def unmarshal_list(self, data):
        try:
            return self.normalize_list(self.library.loads(data))
        except Exception as e:
            raise error.UnmarshalError(str(e))

    def unmarshal_dict(self, data):
        try:
            return self.normalize_dict(self.library.loads(data))
        except Exception as e:
            raise error.UnmarshalError(str(e))


class Pickle3ContentHandler(PickleContentHandler):
    """Handler for pickle-encoded content, protocol level version 3.

    This version is only supported by the Python3 version the pickle module, this ContentHandler is
    only usable in Python3.

    .. seealso:: `module documentation <http://docs.python.org/3/library/pickle.html>`_,
       `WikiPedia <http://en.wikipedia.org/wiki/Pickle_(Python)>`_
    """

    mime = 'application/pickle3'
    """The mime-type used by this content handler is 'application/pickle3'."""

    PROTOCOL = 3


class YAMLContentHandler(ContentHandler):
    """Handler for YAML encoded content.

    .. NOTE:: This ContentHandler requires the ``PyYAML`` library to be installed.

    .. seealso:: `Specification <http://www.yaml.org/>`_, `WikiPedia
      <http://en.wikipedia.org/wiki/YAML>`_, `PyYAML <https://pypi.python.org/pypi/PyYAML>`_ on
      PyPI
    """
    mime = 'application/yaml'
    """The mime-type used by this content handler is 'application/yaml'."""

    librarypath = 'yaml'

    def _marshal_str3(self, obj):  # pragma: py3
        return self.library.dump(self.normalize_str(obj), encoding='utf-8')

    def _py2_str_helper(self, s):  # pragma: py2
        """Wrap eratic behaviour of the Python2 YAML implementation.

        In Python2, the YAML implentation is unfortunately very eratic. Here is what the
        documentation says:

        * str objects are converted into !!str, !!python/str or !binary nodes depending on whether
          the object is an ASCII, UTF-8 or binary string.
        * unicode objects are converted into !!python/unicode or !!str nodes depending on whether
          the object is an ASCII string or not.

        This is unfortunately unreproduceable::

            >>> import yaml
            >>> yaml.dump('a')  # (a) this result is correct
            'a\n...\n'
            >>> yaml.dump(u'a')  # (b) unicode object returns non-portable !!python/unicode
            "!!python/unicode 'a'\n"
            >>> yaml.dump(u'a'.encode('utf-8'))  # same as yaml.dump('a')
            'a\n...\n'
            >>> yaml.dump(u'foo愑')  # (c) non-ascii unicode returns portable str
            '"foo\\u6111"\n'
            >>> yaml.dump(u'foo愑'.encode('utf-8'))  # (d) str returns non-portable !!python/str
            '!!python/str "foo\\u6111"\n'

        So to summarize, this method does::

        * cast unicode to str if it is ASCII, so (b) is converted to (a)
        * cast a str object to unicode if it non-ASCII: (d) is converted (c)
        """
        if type(s) == unicode:
            try:
                s.decode('utf-8')
                return s.encode('utf-8')
            except UnicodeEncodeError:
                pass
        elif type(s) == str:
            try:
                s.encode('utf-8')
                return s
            except UnicodeDecodeError:
                return s.decode('utf-8')
        return s

    def _marshal_str2(self, obj):  # pragma: py2
        return self.library.dump(self._py2_str_helper(obj))

    def marshal_str(self, obj):
        try:
            return self._marshal_str(obj)
        except Exception as e:
            raise error.MarshalError(e)

    def _marshal_dict3(self, obj):  # pragma: py3
        return self.library.dump(self.normalize_dict(obj), encoding='utf-8')

    def _py2_dict_helper(self, d):  # pragma: py2
        def conv(v):
            if isinstance(v, unicode):
                return self._py2_str_helper(v)
            elif isinstance(v, dict):
                return self._py2_dict_helper(v)
            return v

        return dict((conv(k), conv(v)) for k, v in d.iteritems())

    def _marshal_dict2(self, obj):  # pragma: py2
        return self.library.dump(self._py2_dict_helper(obj))

    def marshal_dict(self, obj):
        try:
            return self._marshal_dict(obj)
        except Exception as e:
            raise error.MarshalError(e)

    def _marshal_list3(self, obj):  # pragma: py3
        return self.library.dump(self.normalize_list(obj), encoding='utf-8')

    def _marshal_list2(self, obj):  # pragma: py2
        return self.library.dump([self._py2_str_helper(s) for s in obj])

    def marshal_list(self, obj):
        try:
            return self._marshal_list(obj)
        except Exception as e:
            raise error.MarshalError(e)

    def unmarshal_str(self, data):
        try:
            unmarshalled = self.library.load(data)
            return self.normalize_str(unmarshalled)
        except self.library.YAMLError as e:  # pragma: no cover
            raise error.UnmarshalError(e)

    def unmarshal_list(self, data):
        try:
            return self.normalize_list(self.library.load(data))
        except self.library.YAMLError as e:
            raise error.UnmarshalError(e)

    def unmarshal_dict(self, data):
        try:
            return self.normalize_dict(self.library.load(data))
        except self.library.YAMLError as e:
            raise error.UnmarshalError(e)

    if PY3:  # pragma: py3
        _marshal_str = _marshal_str3
        _marshal_dict = _marshal_dict3
        _marshal_list = _marshal_list3
    else:  # pragma: py2
        _marshal_str = _marshal_str2
        _marshal_dict = _marshal_dict2
        _marshal_list = _marshal_list2


class XMLContentHandler(ContentHandler):
    """Handler for XML encoded data.

    .. NOTE:: This ContentHandler requires the ``lxml`` library to be installed.

    .. seealso:: `lxml <https://pypi.python.org/pypi/lxml>`_ on PyPI
    """

    mime = 'application/xml'
    """The mime-type used by this content handler is 'application/xml'."""

    librarypath = 'lxml.etree'

    def unmarshal_str(self, data):
        text = self.library.fromstring(data).text
        if text is None:
            text = ''

        return self.normalize_str(text)

    def _unmarshal_dict(self, tree):
        d = {}

        # find all strings
        for e in tree.iterfind('str'):
            if e.text is None:
                d[e.attrib['key']] = ''
            else:
                d[e.attrib['key']] = e.text

        # parse subdictionaries
        for subdict in tree.iterfind('dict'):
            d[subdict.attrib['key']] = self._unmarshal_dict(subdict)
        for sublist in tree.iterfind('list'):
            d[sublist.attrib['key']] = self._unmarshal_list(sublist)

        return d

    def unmarshal_dict(self, body):
        d = self._unmarshal_dict(self.library.fromstring(body))
        return self.normalize_dict(d)

    def _unmarshal_list(self, tree):
        l = []
        for elem in tree.iterfind('str'):
            if elem.text is None:
                l.append('')
            else:
                l.append(elem.text)
        return self.normalize_list(l)

    def unmarshal_list(self, body):
        return self._unmarshal_list(self.library.fromstring(body))

    def marshal_str(self, obj):
        try:
            obj = self.normalize_str(obj)
            root = self.library.Element('str')
            root.text = obj
            return self.library.tostring(root)
        except Exception as e:
            raise error.MarshalError(e)

    def _marshal_list(self, obj, key=None):
        try:
            obj = self.normalize_list(obj)

            root = self.library.Element('list')
            if key is not None:
                root.attrib['key'] = key
            for value in obj:
                elem = self.library.Element('str')
                elem.text = value
                root.append(elem)
            return root
        except Exception as e:
            raise error.MarshalError(e)

    def marshal_list(self, obj):
        return self.library.tostring(self._marshal_list(obj))

    def _marshal_dict(self, obj, key=None):
        root = self.library.Element('dict')
        if key is not None:
            root.attrib['key'] = key

        obj = self.normalize_dict(obj)

        for key, value in obj.items():
            if isinstance(value, dict):
                root.append(self._marshal_dict(value, key=key))
            elif isinstance(value, list):
                root.append(self._marshal_list(value, key=key))
            else:
                elem = self.library.Element('str', attrib={'key': key})
                elem.text = value
                root.append(elem)
        return root

    def marshal_dict(self, obj):
        try:
            s = self.library.tostring(self._marshal_dict(obj))
            return s
        except Exception as e:
            raise error.MarshalError(e)


CONTENT_HANDLERS = {
    'application/bson': BSONContentHandler,
    'application/json': JSONContentHandler,
    'application/messagepack': MessagePackContentHandler,
    'application/pickle': PickleContentHandler,
    'application/pickle3': Pickle3ContentHandler,
    'application/x-www-form-urlencoded': FormContentHandler,
    'application/xml': XMLContentHandler,
    'application/yaml': YAMLContentHandler,
}
"""
Mapping of MIME types to their respective handler implemenation. You can use this dictionary to
dynamically look up a content handler if you do not know the requested content type in advance.

================================= ===============================================
MIME type                         Handler
================================= ===============================================
application/json                  :py:class:`.handlers.JSONContentHandler`
application/x-www-form-urlencoded :py:class:`.handlers.FormContentHandler`
application/pickle                :py:class:`.handlers.PickleContentHandler`
application/pickle3               :py:class:`.handlers.Pickle3ContentHandler`
application/xml                   :py:class:`.handlers.XMLContentHandler`
application/yaml                  :py:class:`.handlers.YAMLContentHandler`
application/bson                  :py:class:`.handlers.BSONContentHandler`
application/messagepack           :py:class:`.handlers.MessagePackContentHandler`
================================= ===============================================

If you want to provide your own implementation of a :py:class:`.ContentHandler`, you can add it to
this dictionary with the appropriate MIME type as the key.
"""
