#!/usr/bin/env python

# Convert reservoir Earth model to exodus mesh

import numpy as np
from readers import eclipse, leapfrog
from exodus_model import ExodusModel
import argparse
import os
import sys

def _load_config(path):
    ''' Load a YAML config file. The file must contain a mapping from option
    `dest` names (e.g. `refine_xy`, `extract_i`, `extra_keywords`) to values.
    Lists are written as YAML sequences; booleans as `true` / `false`.
    Returns the loaded dict. '''
    import yaml
    if not os.path.exists(path):
        sys.exit("Config file not found: {}".format(path))
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        sys.exit("Config file must contain a YAML mapping (got {})".format(type(cfg).__name__))
    return cfg

def _build_config_key_mapping(parser):
    ''' Build a mapping from acceptable config-file key names to canonical
    argparse `dest` names. The user can write any of:

      - the CLI flag name with leading dashes stripped (e.g. `refine-xy`)
      - the CLI flag name with hyphens converted to underscores (`refine_xy`)
      - the argparse `dest` itself (also `refine_xy` here, but for options like
        `--flip` -> `flip_z` or `--force` -> `force_overwrite` the dest is
        different from the flag and both forms are accepted)

    Short options (e.g. `-f`) are deliberately excluded to keep the config
    keys descriptive. Returns (mapping, valid_canonical_keys).
    '''
    mapping = {}
    canonical = []
    for action in parser._actions:
        if action.dest == 'help':
            continue
        canonical.append(action.dest)
        # The dest itself is always accepted.
        mapping[action.dest] = action.dest
        # Each long-option flag is also accepted (after stripping `--` and
        # normalising hyphens to underscores).
        for opt in action.option_strings:
            stripped = opt.lstrip('-')
            if len(stripped) < 2:
                continue   # skip short flags like -f / -o / -u
            mapping[stripped.replace('-', '_')] = action.dest
    return mapping, sorted(canonical)


def _validate_and_normalize_config(cfg, parser):
    ''' Resolve every config key to its canonical `dest` name. Accepts the
    flexible forms documented in _build_config_key_mapping; rejects anything
    that doesn't match any option, listing the valid keys.

    Returns a new dict keyed by canonical `dest` names. '''
    mapping, canonical = _build_config_key_mapping(parser)
    normalized = {}
    unknown = []
    for key, value in cfg.items():
        candidate = key.lstrip('-').replace('-', '_')
        if candidate in mapping:
            normalized[mapping[candidate]] = value
        else:
            unknown.append(key)
    if unknown:
        sys.exit(
            "Unknown keys in config file: {}\n"
            "Valid keys (or any long CLI flag name with leading dashes\n"
            "stripped and hyphens converted to underscores): {}".format(
                ', '.join(unknown), ', '.join(canonical)))
    return normalized

def _positive_int(s):
    ''' argparse type for strictly positive integers (refinement factors and
    extract indices). '''
    try:
        v = int(s)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "expected a positive integer, got {!r}".format(s))
    if v < 1:
        raise argparse.ArgumentTypeError(
            "expected a positive integer (>= 1), got {}".format(v))
    return v

def _eclipse_keyword(s):
    ''' argparse type for an Eclipse property keyword. Normalises to uppercase
    and rejects anything that isn't a short alphanumeric token. '''
    up = s.upper()
    if not up or not up.isalnum() or len(up) > 8:
        raise argparse.ArgumentTypeError(
            "expected a short alphanumeric Eclipse keyword (<= 8 chars), got {!r}".format(s))
    return up

def get_parser():
    ''' Read commandline options and filename '''

    parser = argparse.ArgumentParser(description='Converts earth model to Exodus II format')
    parser.add_argument('filename', nargs='?', default=None,
        help='Input reservoir model file. Optional only when provided via --config.')
    parser.add_argument('--config', dest='config_file', default=None, metavar='FILE',
        help='YAML config file specifying default values for any of this script\'s options. Values from the config are overridden by command-line flags. Use the option\'s `dest` name as the key (e.g. refine_xy, extract_i, extra_keywords).')
    parser.add_argument('-o', '--output', default = None, dest = 'output_file', help = 'File name for output')
    parser.add_argument('--filetype', default = None, dest = 'filetype',
        choices = ['eclipse', 'leapfrog'], help = 'Explicitly state the filetype for unknown extensions')
    parser.add_argument('--no-nodesets', dest = 'omit_nodesets', action = 'store_true', help = 'Disable addition of nodesets')
    parser.add_argument('--no-sidesets', dest = 'omit_sidesets', action = 'store_true', help = 'Disable addition of sidesets')
    parser.add_argument('-f', '--force', dest = 'force_overwrite', action = 'store_true', help = 'Overwrite filename.e if it exists')
    parser.add_argument('-u', '--use-official-api', dest = 'use_official_api', action = 'store_true', help = 'Use exodus.py to write files')
    parser.add_argument('--flip', dest = 'flip_z', action = 'store_true', help = 'Flip the sign of the Z coordinates')
    parser.add_argument('--translate', nargs = 2, dest = 'translate', type = float, help = 'Translate the (x, y) coordinates by this amount')
    parser.add_argument('--mapaxes', dest = 'use_mapaxes', action = 'store_true', help = 'Use the MAPAXES coordinates for an Eclipse file')
    parser.add_argument('--pinch', default = False, dest = 'no_pinch', action = 'store_true', help = 'Remove pinched elements (coincident corners within --pinch-tol). Off by default; faithful conversion is produced without this flag.')
    parser.add_argument('--pinch-tol', default = 1e-3, dest = 'pinch_tol', type = float, help = 'Tolerance for coincident corners when removing pinched elements (default: 1e-3)')
    parser.add_argument('--refine-xy', nargs = 2, dest = 'refine_xy', type = _positive_int,
        metavar = ('RX', 'RY'),
        help = 'Refine the grid laterally by integer factors RX in x and RY in y (vertical resolution unchanged). Each child cell inherits its parent\'s element properties.')
    parser.add_argument('--extract-i', nargs = 2, dest = 'extract_i', type = _positive_int,
        metavar = ('I_LO', 'I_HI'),
        help = 'Extract cells I_LO..I_HI along the x-axis (1-based inclusive, Eclipse-style). Cells are taken in file order, before any coordinate-system normalisation; runs before --refine-xy if both are given.')
    parser.add_argument('--extract-j', nargs = 2, dest = 'extract_j', type = _positive_int,
        metavar = ('J_LO', 'J_HI'),
        help = 'Extract cells J_LO..J_HI along the y-axis (1-based inclusive).')
    parser.add_argument('--extract-k', nargs = 2, dest = 'extract_k', type = _positive_int,
        metavar = ('K_LO', 'K_HI'),
        help = 'Extract cells K_LO..K_HI along the z-axis (1-based inclusive).')
    parser.add_argument('--extra-keywords', nargs = '+', dest = 'extra_keywords',
        type = _eclipse_keyword, metavar = 'KEY',
        help = 'Additional per-cell property keywords to read from the grdecl file (e.g. PVTNUM EQLNUM FIPNUM). Each must be a per-cell scalar of length NX*NY*NZ. Normalised to uppercase. The reader recognises ACTNUM, SATNUM, PORO, PERMX, PERMY, PERMZ, NTG, HEATCR and THCONR by default.')
    parser.add_argument('--fault-sidesets', dest = 'fault_sidesets', action = 'store_true',
        help = 'Emit paired sidesets named "fault_primary" and "fault_secondary" containing the faces on either side of every fault (any internal face where adjacent cells do not share their corner nodes).')
    parser.add_argument('--convert-to-m', dest = 'convert_to_m', action = 'store_true',
        help = 'Convert grid coordinates to metres on output, using the input file\'s GRIDUNIT keyword as the source unit. Supported values are METRES (no-op), FEET and CM. Files without GRIDUNIT are assumed to be in metres.')
    parser.add_argument('--no-check-jacobians', dest = 'check_jacobians', action = 'store_false',
        help = 'Skip the per-element Jacobian sanity check. By default em2ex computes the Jacobian at all 8 corners of every HEX8 element and warns if any are non-positive (degenerate or inverted), since those elements would be rejected by most FEM solvers.')
    parser.add_argument('--strict-jacobians', dest = 'strict_jacobians', action = 'store_true',
        help = 'Treat any non-positive element Jacobian as a fatal error and exit non-zero. By default such elements only produce a warning. Useful for CI / scripted workflows.')
    parser.add_argument('--remove-distorted', dest = 'remove_distorted', action = 'store_true',
        help = 'Remove elements with non-positive Jacobians (degenerate or inverted) from the output mesh, reporting a count of those removed. By default such elements are kept and only a warning is printed.')
    return parser

def main():
    ''' Parse the Earth model and write out an Exodus II file '''

    # Parse commandline options. If --config is given, load the YAML file and
    # apply its values as parser defaults; command-line flags then override
    # those defaults in the usual way (precedence: CLI > config > parser default).
    parser = get_parser()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--config', dest='config_file', default=None)
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.config_file:
        config = _load_config(pre_args.config_file)
        config = _validate_and_normalize_config(config, parser)
        parser.set_defaults(**config)
    args = parser.parse_args()

    if not args.filename:
        parser.error('filename is required (provide as a positional argument or as `filename: ...` in --config)')

    # If --use-official-api is passed, then import exodus from exodus.py. Note:
    # this requires that exodus.py is in the $PYTHONPATH environment variable
    if args.use_official_api:
        from exodus import exodus
    else:
        from pyexodus.pyexodus import exodus

    # Extract file name and extension
    filename = args.filename
    filename_base, file_extension = os.path.splitext(filename)

    # Override the file extension in the input file using the --filetype argument
    if args.filetype == 'eclipse':
        file_extension = '.grdecl'

    elif args.filetype == 'leapfrog':
        file_extension = ''

    # Parse the reservoir model using the appropriate reader
    if file_extension.lower() == ".grdecl":
        model = eclipse.parseEclipse(filename, args)

    elif file_extension == '':
        model = leapfrog.parseLeapfrog(filename, args)

    else:
        print('File extension ', file_extension, ' not supported')
        exit()

    # Mesh quality: check element Jacobians before writing the Exodus file.
    # Default is to warn but continue; --strict-jacobians upgrades to a fatal
    # error; --no-check-jacobians skips the check entirely.
    if getattr(args, 'check_jacobians', True):
        from readers.reader_utils import checkElementJacobians
        checkElementJacobians(model, strict=getattr(args, 'strict_jacobians', False))

    # After parsing the reservoir model, the Exodus file can be written
    # Model dimension (default is 3)
    numDim = model.dim

    # Number of nodes, elements, sidesets and nodesets
    numNodes = model.numNodes
    numElems = model.numElems
    numNodeSets = model.numNodeSets
    numSideSets = model.numSideSets

    # The number of blocks is equal to the unique numbers of block ids
    blocks = model.blockIds
    block_ids = np.unique(blocks)
    numBlocks = len(block_ids)

    exodusTitle = 'Converted from ' + filename + ' by em2ex.py'

    coordNames = ["x", "y", "z"]
    elemType = 'HEX8'
    nodesPerElem = 8

    # Output file
    if args.output_file:
        output_file = args.output_file
    else:
        output_file = filename_base + '.e'

    # If force_overwrite, then clobber any exisiting filename_base.e file
    if args.force_overwrite and os.path.exists(output_file):
        try:
            os.remove(output_file)
        except:
            print("Cannot delete ", output_file)

    # Write the exodus file using the exodus python API
    exodusFile = exodus(output_file,
                        'w',
                        'numpy',
                        exodusTitle,
                        numDim,
                        numNodes,
                        numElems,
                        numBlocks,
                        numNodeSets,
                        numSideSets)

    exodusFile.put_coord_names(coordNames)
    exodusFile.put_coords(model.xcoords, model.ycoords, model.zcoords)

    exodusFile.put_elem_blk_names(block_ids.astype(str))

    # Put all the element connectivities per block
    for blkid in block_ids:
        numElemsInBlock = blocks[blocks==blkid].size
        exodusFile.put_elem_blk_info(blkid, elemType, numElemsInBlock, nodesPerElem, 0)
        exodusFile.put_elem_connectivity(blkid, model.elemNodes[blocks.flatten()==blkid].flatten())

    if not args.omit_nodesets:
        exodusFile.put_node_set_names(model.nodeSetNames)

        for i in range(numNodeSets):
                exodusFile.put_node_set_params(i, len(model.nodeSets[i]))
                exodusFile.put_node_set(i, model.nodeSets[i])

    if not args.omit_sidesets:
        exodusFile.put_side_set_names(model.sideSetNames)

        for i in range(numSideSets):
                exodusFile.put_side_set_params(i, len(model.sideSets[i]), 0)
                exodusFile.put_side_set(i, model.sideSets[i], model.sideSetSides[i])

    # Only want a single time step (t = 0) for this exodus file
    timestep = 1
    time = 0
    exodusFile.put_time(timestep, time)

    # Add any elemental reservoir properties as elemental variables
    if model.elemVars:
        exodusFile.set_element_variable_number(len(model.elemVars))

        var_counter = 1
        for var in model.elemVars:
            exodusFile.put_element_variable_name(var.lower(), var_counter)
            var_counter += 1

        for blkid in block_ids:
            for var in model.elemVars:
                exodusFile.put_element_variable_values(blkid, var.lower(), timestep, model.elemVars[var][blocks==blkid])

        # Add elemental variables to sidesets as well if required
        if not args.omit_sidesets:
            exodusFile.set_side_set_variable_number(len(model.elemVars))

            var_counter = 1
            for var in model.elemVars:
                exodusFile.put_side_set_variable_name(var.lower(), var_counter)
                var_counter += 1

            # Add elemental variable values at each side in each sideset
            for var in model.elemVars:
                for i in range(numSideSets):
                    exodusFile.put_side_set_variable_values(i, var.lower(), timestep, model.elemVars[var].take(np.asarray(model.sideSets[i]) - 1))

    # Add any nodal variable values
    if model.nodeVars:
        exodusFile.set_node_variable_number(len(model.nodeVars))

        var_counter = 1
        for var in model.nodeVars:
            exodusFile.put_node_variable_name(var.lower(), var_counter)
            var_counter += 1

        for var in model.nodeVars:
            exodusFile.put_node_variable_values(var.lower(), timestep, model.nodeVars[var])

        # Add nodal variables to nodesets as well if required
        if not args.omit_nodesets:
            exodusFile.set_node_set_variable_number(len(model.nodeVars))

            var_counter = 1
            for var in model.nodeVars:
                exodusFile.put_node_set_variable_name(var.lower(), var_counter)
                var_counter += 1

            # Add nodal variable values at each node in each nodeset
            for var in model.nodeVars:
                for i in range(numNodeSets):
                    exodusFile.put_node_set_variable_values(i, var.lower(), timestep, model.nodeVars[var].take(np.asarray(model.nodeSets[i]) - 1))

    # Finally, close the exodus file
    exodusFile.close()

    print('Exodus file written to {}'.format(output_file))

if __name__ == '__main__':
    main()
