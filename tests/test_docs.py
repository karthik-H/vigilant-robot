import os
import fnmatch
import subprocess

import pytest

from utils import TESTS_ROOT


def has_docutils():
    """
    Checks whether the 'docutils' Python package is installed.
    
    Returns:
        True if 'docutils' can be imported, otherwise False.
    """
    try:
        # noinspection PyUnresolvedReferences
        import docutils
        return True
    except ImportError:
        return False


def rst_filenames():
    """
    Yields the full paths of all .rst files under the parent directory of TESTS_ROOT, excluding any directories containing '.tox'.
    
    This generator recursively traverses the directory tree and yields each reStructuredText file found.
    """
    for root, dirnames, filenames in os.walk(os.path.dirname(TESTS_ROOT)):
        if '.tox' not in root:
            for filename in fnmatch.filter(filenames, '*.rst'):
                yield os.path.join(root, filename)


filenames = list(rst_filenames())
assert filenames


@pytest.mark.skipif(not has_docutils(), reason='docutils not installed')
@pytest.mark.parametrize('filename', filenames)
def test_rst_file_syntax(filename):
    """
    Tests the syntax of a reStructuredText (.rst) file using rst2pseudoxml.py.
    
    Asserts that the file passes syntax validation by checking that rst2pseudoxml.py exits with a zero return code. If validation fails, the test outputs the error message.
    """
    p = subprocess.Popen(
        ['rst2pseudoxml.py', '--report=1', '--exit-status=1', filename],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    err = p.communicate()[1]
    assert p.returncode == 0, err
