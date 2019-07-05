#!/usr/bin/env python

# Convert reservoir Earth model to exodus mesh

import numpy as np
from readers import eclipse, leapfrog
from exodus_model import ExodusModel
import argparse
import os

def get_parser():
    ''' Read commandline options and filename '''

    parser = argparse.ArgumentParser(description='Converts earth model to Exodus II format')
    parser.add_argument('filename')
    parser.add_argument('--filetype', default = None, dest = 'filetype',
        choices = ['eclipse', 'leapfrog'], help = 'Explicitly state the filetype for unknown extensions')
    parser.add_argument('--no-nodesets', dest = 'omit_nodesets', action = 'store_true', help = 'Disable addition of nodesets')
    parser.add_argument('--no-sidesets', dest = 'omit_sidesets', action = 'store_true', help = 'Disable addition of sidesets')
    parser.add_argument('-f', '--force', dest = 'force_overwrite', action = 'store_true', help = 'Overwrite filename.e if it exists')
    parser.add_argument('-u', '--use-official-api', dest = 'use_official_api', action = 'store_true', help = 'Use exodus.py to write files')
    return parser

def main():
    ''' Parse the Earth model and write out an Exodus II file '''

    # Parse commandline options
    parser = get_parser()
    args = parser.parse_args()

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
    if file_extension == ".grdecl":
        model = eclipse.parseEclipse(filename, args)

    elif file_extension == '':
        model = leapfrog.parseLeapfrog(filename, args)

    else:
        print('File extension ', file_extension, ' not supported')
        exit()

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

    # If force_overwrite, then clobber any exisiting filename_base.e file
    output_file = filename_base + '.e'

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
