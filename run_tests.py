#!/usr/bin/env python

import subprocess
import pytest
import os
import yaml

# Exception class to throw exception for pytest
class Em2exException(Exception):
    pass

# Run the current file using pytest
pytest.main(['-v', '-rsx', '--tb=line', 'run_tests.py'])

# Find all 'tests' yml files that contain the test specifications
tests_files = []
for root, dirs, files in os.walk("test/", topdown=False):
    for name in files:
        if name == 'tests':
            tests_files.append(os.path.join(root, name))

# Read yaml data from tests files
tests = {}
for test in tests_files:
    with open(test, 'r') as file:
        testcfg = yaml.safe_load(file)
        for key, values in testcfg.items():
            tests[key] = values
            # Also save the filepath to the dict
            filename_path, filename = os.path.split(test)
            tests[key]['filepath'] = filename_path

# Run all em2ex tests found during search
@pytest.mark.parametrize('key', tests)
def test_em2ex(key):
    ''' Run all em2ex tests using appropriate test function '''

    # If the type key isn't specified, skip test
    if 'type' not in tests[key].keys():
        pytest.skip(tests[key]['filepath'] + '/tests:' + key + ': Skipped as test type not specified')

    # If the filename key isn't specified, skip test
    if 'filename' not in tests[key].keys():
        pytest.skip(tests[key]['filepath'] + '/tests:' + key + ': Skipped as file not specified')

    # If the test type is exodiff, run exodiff_test
    if tests[key]['type'] == 'exodiff':
        # If the gold key isn't specified, skip test
        if 'gold' not in tests[key].keys():
            pytest.skip(tests[key]['filepath'] + '/tests:' + key + ': Skipped as gold file not specified')
        else:
            exodiff_test(key)

    # If the test type is exception, run the expected_error test
    if tests[key]['type'] == 'exception':
        # If the expected_error key isn't specified, skip test
        if 'expected_error' not in tests[key].keys():
            pytest.skip(tests[key]['filepath'] + '/tests:' + key + ': Skipped as expected_error not specified')
        else:
            with pytest.raises(Exception) as excinfo:
                expected_error(key)

            assert tests[key]['expected_error'] in str(excinfo.value)

    return

def exodiff_test(key):
    ''' Convert reservoir model to exodus and compare with gold file '''

    # Convert reservoir model to Exodus II model
    filepath = tests[key]['filepath']

    filename = tests[key]['filename']
    testfilename = os.path.join(filepath, filename)
    subprocess.check_output(['./em2ex.py', '-f', testfilename])

    # Compare the converted model with a gold file using exodiff
    try:
        filename_base, file_extension = os.path.splitext(filename)
        exodus_filename = os.path.join(filepath, filename_base + '.e')
        gold_filename = os.path.join(filepath, 'gold', tests[key]['gold'])
        subprocess.check_output(['exodiff', '-quiet', exodus_filename, gold_filename])

    except subprocess.CalledProcessError:
        raise Em2exException( filepath + '/' + key + ': exodiff failed - files are different')

    return

def expected_error(key):
    ''' Raise an exception when an error is thrown while em2ex is running '''

    # Convert reservoir model to Exodus II model
    filepath = tests[key]['filepath']

    filename = tests[key]['filename']
    testfilename = os.path.join(filepath, filename)
    output = subprocess.check_output(['./em2ex.py', '-f', testfilename])

    raise Em2exException(output)

    return
