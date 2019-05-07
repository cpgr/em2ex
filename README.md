# One-step conversion from reservoir Earth models to Exodus II format

## Setup

`em2ex` requires the `exodus` package (including the python API) to be installed. This can be done by installing the [`seacas`](https://github.com/gsjaardema/seacas) package.

For [MOOSE](http://www.mooseframework.org) users, this package is installed as part of
the environment. To use the python API available in this way, the path to the python API in the seacas package (`/opt/moose/seacas/lib`) should be added to the `PYTHONPATH` environment variable.

## Usage

To convert a reservoir model to an Exodus II file, run

```
em2ex.py filename
```

which produces an Exodus II file `filenanem.e` with the reservoir properties saved as elemental (cell-centred) variables.

For example, the `test` directory contains an ASCII Eclipse reservoir model (`.grdecl` file extension). This can be converted to an Exodus II file using
```
em2ex.py test.grdecl
```
