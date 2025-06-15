"""
Python 2.6, 2.7, and 3.x compatibility.

"""
import sys


is_py2 = sys.version_info[0] == 2
is_py26 = sys.version_info[:2] == (2, 6)
is_py27 = sys.version_info[:2] == (2, 7)
is_py3 = sys.version_info[0] == 3
is_pypy = 'pypy' in sys.version.lower()
is_windows = 'win32' in str(sys.platform).lower()


if is_py2:
    bytes = str
    str = unicode
elif is_py3:
    str = str
    bytes = bytes


try:  # pragma: no cover
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import urlsplit
except ImportError:  # pragma: no cover
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urlparse import urlsplit

try:  # pragma: no cover
    # noinspection PyCompatibility
    from urllib.request import urlopen
except ImportError:  # pragma: no cover
    # noinspection PyCompatibility
    from urllib2 import urlopen

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    # Python 2.6 OrderedDict class, needed for headers, parameters, etc .###
    # <https://pypi.python.org/pypi/ordereddict/1.1>
    # noinspection PyCompatibility
    from UserDict import DictMixin

    # noinspection PyShadowingBuiltins
    class OrderedDict(dict, DictMixin):
        # Copyright (c) 2009 Raymond Hettinger
        #
        # Permission is hereby granted, free of charge, to any person
        # obtaining a copy of this software and associated documentation files
        # (the "Software"), to deal in the Software without restriction,
        # including without limitation the rights to use, copy, modify, merge,
        # publish, distribute, sublicense, and/or sell copies of the Software,
        # and to permit persons to whom the Software is furnished to do so,
        # subject to the following conditions:
        #
        #     The above copyright notice and this permission notice shall be
        #     included in all copies or substantial portions of the Software.
        #
        #     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
        #     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
        #     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
        #     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
        #     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
        #     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
        #     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
        #     OTHER DEALINGS IN THE SOFTWARE.
        # noinspection PyMissingConstructor
        def __init__(self, *args, **kwds):
            """
            Initializes a new OrderedDict instance, optionally populating it with data.
            
            Accepts at most one positional argument (an iterable or mapping) and keyword arguments to initialize the dictionary. Raises TypeError if more than one positional argument is provided.
            """
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d'
                                % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            """
            Removes all items from the dictionary while preserving the insertion order structure.
            
            Resets the internal linked list and mapping used to maintain key order.
            """
            self.__end = end = []
            # noinspection PyUnusedLocal
            end += [None, end, end]     # sentinel node for doubly linked list
            self.__map = {}             # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            """
            Adds or updates a key-value pair, preserving insertion order.
            
            If the key is new, it is appended to the end of the ordered sequence; if the key exists, its value is updated without changing its position.
            """
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            """
            Removes the specified key and its associated value, maintaining insertion order.
            
            Deletes the key from the dictionary and updates the internal linked list to preserve order.
            """
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            """
            Iterates over the keys of the OrderedDict in insertion order.
            
            Yields:
                Keys in the order they were added to the dictionary.
            """
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            """
            Iterates over the keys of the OrderedDict in reverse insertion order.
            
            Yields:
                Keys in the order opposite to their insertion.
            """
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            """
            Removes and returns a (key, value) pair from the dictionary.
            
            Args:
                last: If True, removes the most recently inserted item; otherwise, removes the earliest inserted item.
            
            Returns:
                A tuple containing the key and value of the removed item.
            
            Raises:
                KeyError: If the dictionary is empty.
            """
            if not self:
                raise KeyError('dictionary is empty')
            if last:
                key = reversed(self).next()
            else:
                key = iter(self).next()
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            """
            Supports pickling of the OrderedDict by returning its constructor arguments and instance state.
            
            Returns:
                A tuple containing the class, initialization arguments, and optionally the instance dictionary for pickling.
            """
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return self.__class__, (items,), inst_dict
            return self.__class__, (items,)

        def keys(self):
            """
            Returns a list of keys in insertion order.
            """
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            """
            Return a string representation of the OrderedDict, showing its class name and items.
            """
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            """
            Returns a shallow copy of the OrderedDict instance.
            """
            return self.__class__(self)

        # noinspection PyMethodOverriding
        @classmethod
        def fromkeys(cls, iterable, value=None):
            """
            Creates a new OrderedDict with keys from the given iterable, each mapped to the specified value.
            
            Args:
                iterable: An iterable of keys to include in the new OrderedDict.
                value: The value assigned to each key. Defaults to None.
            
            Returns:
                An OrderedDict instance with the specified keys and values.
            """
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            """
            Checks equality with another object, considering both item order and content.
            
            Returns True if the other object is an OrderedDict with the same items in the same order; otherwise, falls back to standard dictionary equality.
            """
            if isinstance(other, OrderedDict):
                if len(self) != len(other):
                    return False
                for p, q in zip(self.items(), other.items()):
                    if p != q:
                        return False
                return True
            return dict.__eq__(self, other)

        def __ne__(self, other):
            """
            Returns True if this OrderedDict is not equal to another object.
            
            Inequality is determined by comparing both the order and content of items if the other object is an OrderedDict; otherwise, falls back to standard dictionary comparison.
            """
            return not self == other
