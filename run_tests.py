#!/usr/bin/env python

import subprocess
import pytest
import os

# Exception class to throw exception for pytest
class ExodiffException(Exception):
    pass

# Run the current file using pytest
pytest.main(['-v', 'run_tests.py'])

# List of exodiff tests (add new tests to list here)
exodiff_tests = ['test/eclipse/test.grdecl',
                 'test/leapfrog/test',
                 'test/leapfrog/irr_test']

# The exodiff test iterates over the list of tests in exodiff_tests
# and runs test_exodiff() on each of them
@pytest.mark.parametrize('test', [i for i in exodiff_tests])
def test_exodiff(test):
    # Convert reservoir model to Exodus II model
    subprocess.check_output(['./em2ex.py', '-f', test])

    # Compare the converted model with a gold file using exodiff
    try:
        filename_base, file_extension = os.path.splitext(test)
        filename_path, filename = os.path.split(filename_base)

        subprocess.check_output(['exodiff', '-quiet', filename_base + '.e', filename_path + '/gold/' + filename + '.e'])

    except subprocess.CalledProcessError:
        raise ExodiffException('Exodiff failed: files are different')
