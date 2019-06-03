# One-step conversion from reservoir Earth models to Exodus II format

[![Build Status](https://travis-ci.com/cpgr/em2ex.svg?branch=master)](https://travis-ci.com/cpgr/em2ex)

`em2ex` converts a reservoir model to an Exodus II file that can then be used in
a simulation tool (such as [MOOSE](http://www.mooseframework.org)). Currently, `em2ex`
supports two reservoir modelling packages:

- Eclipse
- Leapfrog Geothermal

`em2ex` is a python program designed using python 2.7. Current versions of the Exodus II python API that `em2ex` uses **do not work with python 3**, so all users should use python 2.7 at this current time.

## Setup

`em2ex` requires the `exodus` package (including the python API) to be installed. This can be done by installing the [`seacas`](https://github.com/gsjaardema/seacas) package.

For [MOOSE](http://www.mooseframework.org) users, this package is installed as part of
the environment. To use the python API available in this way, the path to the python API in the seacas package (`/opt/moose/seacas/lib`) should be added to the `PYTHONPATH` environment variable
```bash
export PYTHONPATH=$PYTHONPATH:/opt/moose/seacas/lib
```

For non-MOOSE users, the location of `exodus.py` must be added to `PYTHONPATH`.

The following python packages are also required to run `em2ex`

- numpy
- pandas

These are typically already installed, but if not, can be installed using `pip`
```bash
pip install numpy
```

An additional python package, `pytest`, is required to run the test script. Again, this can be installed using
```bash
pip install pytest
```

## Usage

To convert a reservoir model to an Exodus II file, run

```bash
./em2ex.py filename
```

which produces an Exodus II file `filenanem.e` with the cell-centred reservoir properties saved
as elemental variables, and nodal properties saved as nodal variables.

For example, the `test/eclipse` directory contains an ASCII Eclipse reservoir model (`.grdecl` file extension). This can be converted to an Exodus II file using
```bash
./em2ex.py test.grdecl
```

Similarly, the `test/leapfrog` directory contains a set of example Leapfrog reservoir model files that can be converted to Exodus II files using
```bash
./em2ex.py test
```

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

`em2ex` includes a python script `run_tests.py` which uses the [pytest](https://pytest.org) framework to run the included tests. The test suite can be run using
```bash
./run_tests.py
```

The test suite is run automatically on all pull requests to ensure that `em2ex` continues to work as expected.

## Contributors

`em2ex` has been developed by
- Chris Green, CSIRO ([cpgr](https://github.com/cpgr))
- Rob Podgorney, INL ([rpodgorney](https://github.com/rpodgorney))

New contributions are welcome, using the pull request feature of GitHub.

## Feature requests/ bug reports

Any feature requests or bug reports should be made using the issues feature of GitHub. Pull requests are always welcome!
