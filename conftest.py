import pytest

def pytest_addoption(parser):
    parser.addoption('--use-official-api', action = 'store_true', help = 'Use exodus.py to write files (Default is false)')
    parser.addoption('--exodiff', action = 'store', default = 'exodiff', help = 'Specify which exodiff utility to use (Default is exodiff)')

@pytest.fixture
def use_official_api(request):
    return request.config.getoption('--use-official-api')

@pytest.fixture
def exodiff(request):
    return request.config.getoption('--exodiff')
