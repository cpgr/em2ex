# One-step conversion from reservoir Earth models to Exodus II format

[![Build Status](https://travis-ci.com/cpgr/em2ex.svg?branch=master)](https://travis-ci.com/cpgr/em2ex)

`em2ex` is a python program that converts a reservoir model to an Exodus II file that can then be used in
a simulation tool (such as [MOOSE](http://www.mooseframework.org)) or viewed in a visualisation tool (such as [Paraview](https://www.paraview.org)).

Currently, `em2ex` supports two reservoir modelling formats:

- Eclipse (ASCII files)
- Leapfrog Geothermal (CSV files)

## Setup

`em2ex` is a pure python program that does not depend on any external libraries (but does require a few common python packages), so can run on any system with a working python installation.

### Clone repository

`em2ex` can be installed by cloning this repository from GitHub using
```bash
git clone git@github.com:cpgr/em2ex.git
```
or
```bash
git clone https://github.com/cpgr/em2ex.git
```
This will add a folder `em2ex` containing the code.

### Required python packages

The following python packages are required to run `em2ex`

- numpy
- pandas
- netCDF4

The first two are typically already installed, but if not, can be installed using `pip`. The `netCDF4` package can be installed using `pip` as well:
```bash
pip install netdf4
```

Two additional python package, `pytest` and `pyYAML` are required to run the test script. Again, these can be installed using `pip`
```bash
pip install pytest
```

### Optional Exodus API

`em2ex` can optionally use the `Exodus II` API instead of the simplified `pyexodus` API included in the code, which is available through the [`SEACAS`](https://github.com/gsjaardema/seacas) package.

For [MOOSE](http://www.mooseframework.org) users, this package is installed as part of
the default environment. To use the Exodus python API, the path to the python API in the SEACAS package (`/opt/moose/seacas/lib`) should be added to the `PYTHONPATH` environment variable
```bash
export PYTHONPATH=$PYTHONPATH:/opt/moose/seacas/lib
```

For non-MOOSE users, 'SEACAS' can be installed manually and the location of `exodus.py` added to `PYTHONPATH`.

## Usage

To convert a reservoir model to an Exodus II file, run

```bash
./em2ex.py filename
```

which produces an Exodus II file `filenanem.e` with the cell-centred reservoir properties saved
as elemental variables, and nodal properties saved as nodal variables.

For example, the `test/eclipse` directory contains several ASCII Eclipse reservoir model (`.grdecl` file extension). These can be converted to an Exodus II file using
```bash
./em2ex.py simple_cube.grdecl
```

Similarly, the `test/leapfrog` directory contains a set of example Leapfrog reservoir model files that can be converted to Exodus II files using
```bash
./em2ex.py test
```
for example.

## Commandline options

`em2ex` attempts to guess the reservoir model format from the file extension (see supported formats below). If the reservoir model has a non-standard file extension, the user can force
`em2ex` to read the correct format using the `--filetype` commandline option.

For example, if the reservoir model is named `model.dat` but is actually an Eclipse ASCII
file, then `em2ex` can still be used in the following manner
```bash
./em2ex --filetype eclipse model.dat
```

to produce an Exodus II model `test.e`.

## Supported formats

`em2ex` currently supports:

| File format | File extension |
| ----------- | -------------- |
| Eclipse ASCII | `.grdecl`      |
| Leapfrog Geothermal | - |

## Note for Leapfrog Geothermal users

To prepare for usage, several steps must be taken in leapfrog.

First, the user must export a "block model" -- as a CSV with full header data.  Leapfrog gives three options for export of block models,

  1. **CSV Block Model - this option includes the model definition info on the top of the CSV file.  This option is required for use of this tool.**
  2. CSV Block Model + Text File - this option gives the same info as above, but in two files/
  3. CSV Points - a raw dump of the point data

The CSV Block Model file must contain all of the elemental (material property) data--anything that is cell entered.  You will need the rename to file to *filename*_cell.csv

Second, the user will need to create a second block model in Leapfrog that is n+1 bigger and with the base point being nx/2, ny/2, and nz/2 offset--this will make the second mesh centers align with the corners of the first mesh...giving the locations of the nodes.  In Leapfrog, you can interpolate the field estimated pressure and temperature onto this block model.  This second block model must be exported exactly the same as the first one.  You will need to rename the file to *filename*_node.csv

## Test suite

`em2ex` includes a python script `run_tests.py` which uses the [pytest](https://pytest.org) framework to run the included tests.

**Note:** The test suite generates and Exodus file from each reservoir model, and compares it with an existing Exodus file (the gold file). To compare these files, the test harness uses the `exodiff` utility (part of the [`SEACAS`](https://github.com/gsjaardema/seacas) package) to compare Exodus files. If this package is already installed (for example, as part of [MOOSE](http://www.mooseframework.org) or to utilise the Exodus API), then the test suite can be run using
```bash
./run_tests.py
```

Alternatively, to avoid installing the entire [`SEACAS`](https://github.com/gsjaardema/seacas) package) just to run the test suite, the python [`pyexodiff`](https://github.com/cpgr/pyexodiff) package can be installed, and used in the test suite using
```bash
python -m pytest -v --exodiff=pyexodiff.py ./run_tests.py
```

New tests can be added anywhere within the `test` directory. The test harness recurses through this directory and all subdirectories looking for all instances of a `tests` file. This YAML file contains the details of each test in that directory.

The `tests` file syntax is basic YAML, and looks like:
```yml
simple_cube:
  filename: simple_cube.grdecl
  type: exodiff
  gold: simple_cube.e
```
In this example, the test harness will run
```bash
em2ex -f simple_cube.grdecl
```
and then compare the resulting Exodus II file with the file `gold\simple_cube.e`
```bash
exodiff simple_cube.e gold\simple_cube.e
```

The test harness can also test for expected error messages. For example, the follwing block in a `tests` file
```yml
missing_specgrid:
  filename: missing_specgrid.grdecl
  type: exception
  expected_error: No SPECGRID data found
```
will run
```bash
em2ex -f missing_specgrid.grdecl
```
and then check that the error message contains the string `No SPECGRID data found`.

Each `tests` files can contain multiple individual tests. When pytest runs the test suite, the top-level label for each individual test in the `tests` file (for example, the labels `simple_cube` and `missing_specgrid` in the above examples) will be printed to the commandline, along with the status of each test run.

The test suite is run automatically on all pull requests to ensure that `em2ex` continues to work as expected. To reduce the time for automated testing, these tests are run using the provided `pyexodus` API, as well as [`pyexodiff`](https://github.com/cpgr/pyexodiff) to compare the results.

## Contributors

`em2ex` has been developed by
- Chris Green, CSIRO ([cpgr](https://github.com/cpgr))
- Rob Podgorney, INL ([rpodgorney](https://github.com/rpodgorney))

New contributions are welcome, using the pull request feature of GitHub.

## Feature requests/ bug reports

Any feature requests or bug reports should be made using the issues feature of GitHub. Pull requests are always welcome!
