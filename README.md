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

## Commandline options

`em2ex` attempts to guess the reservoir model format from the file extension (see supported formats below). If the reservoir model has a non-standard file extension, the user can force
`em2ex` to read the correct format using the `--filetype` commandline option.

For example, if the reservoir model is named `model.dat` but is actually an Eclipse ASCII
file, then `em2ex` can still be used in the following manner

```
em2ex --filetype eclipse model.dat
```

to produce an Exodus II model `test.e`.

## Supported formats

`em2ex` currently supports:

| File format | File extension |
| ----------- | -------------- |
Eclipse ASCII | `.grdecl`      |
