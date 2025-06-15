from __future__ import division
import json

from httpie.compat import is_py26, OrderedDict


def load_json_preserve_order(s):
    """
    Parses a JSON string while preserving the order of object keys.
    
    If running on Python 2.6, key order is not preserved due to lack of support.
    Otherwise, JSON objects are loaded into an OrderedDict to maintain key order.
    
    Args:
        s: A JSON-formatted string.
    
    Returns:
        The parsed JSON object, with key order preserved when possible.
    """
    if is_py26:
        return json.loads(s)
    return json.loads(s, object_pairs_hook=OrderedDict)


def humanize_bytes(n, precision=2):
    # Author: Doug Latornell
    # Licence: MIT
    # URL: http://code.activestate.com/recipes/577081/
    """
    Converts a byte count into a human-readable string with appropriate units.
    
    Args:
        n: The number of bytes to format.
        precision: Number of decimal places to include in the formatted output.
    
    Returns:
        A string representing the byte count in the largest appropriate unit (B, kB, MB, GB, TB, PB), formatted to the specified precision.
    
    Examples:
        >>> humanize_bytes(1)
        '1 B'
        >>> humanize_bytes(1024, precision=1)
        '1.0 kB'
    """
    abbrevs = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'B')
    ]

    if n == 1:
        return '1 B'

    for factor, suffix in abbrevs:
        if n >= factor:
            break

    # noinspection PyUnboundLocalVariable
    return '%.*f %s' % (precision, n / factor, suffix)
