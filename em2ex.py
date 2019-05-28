#!/usr/bin/env python

# Convert reservoir Earth model to exodus mesh

import numpy as np
from readers import eclipse
from exodus import exodus
from readers import ExodusModel
import argparse
import os

# Read filename and options from commandline
parser = argparse.ArgumentParser(description='Converts earth model to Exodus II format')
parser.add_argument('filename')
parser.add_argument('--filetype', default = None, dest='filetype',
    choices = ['eclipse'], help = 'Explicitly state the filetype for unknown extensions')
args = parser.parse_args()

# Extract file name and extension
filename = args.filename
filename_base, file_extension = os.path.splitext(filename)

# Override the file extension in the input file using the --filetype argument
if (args.filetype == 'eclipse'):
    file_extension = '.grdecl'

# Parse the reservoir model using the appropriate reader
if file_extension == ".grdecl":
    model = eclipse.parseEclipse(filename)

else:
    print 'File extension ', file_extension, ' not supported'
    exit()

# After parsing the reservoir model, the Exodus file can be written
# Nodesets for the boundaries of the model (note: assumes 3D model)
nodeSets = []
nodeSets.append(model.nodeIds[0,:,:].flatten().tolist())
nodeSets.append(model.nodeIds[:,0,:].flatten().tolist())
nodeSets.append(model.nodeIds[:,:,0].flatten().tolist())
nodeSets.append(model.nodeIds[:,:,-1].flatten().tolist())
nodeSets.append(model.nodeIds[:,-1,:].flatten().tolist())
nodeSets.append(model.nodeIds[-1,:,:].flatten().tolist())

# Sidesets for the boundaries of the model (note: assumes 3D model)
sideSets = []
sideSets.append(model.elemIds[0,:,:].flatten().tolist())
sideSets.append(model.elemIds[:,0,:].flatten().tolist())
sideSets.append(model.elemIds[:,:,0].flatten().tolist())
sideSets.append(model.elemIds[:,:,-1].flatten().tolist())
sideSets.append(model.elemIds[:,-1,:].flatten().tolist())
sideSets.append(model.elemIds[-1:,:].flatten())

# Sideset side numbers (note: assumes 3D model)
sideSetSides = []
sideSetSides.append([5]*len(sideSets[0]))
sideSetSides.append([1]*len(sideSets[1]))
sideSetSides.append([4]*len(sideSets[2]))
sideSetSides.append([2]*len(sideSets[3]))
sideSetSides.append([3]*len(sideSets[4]))
sideSetSides.append([6]*len(sideSets[5]))

# Names for each nodeset and sideset
nodeSetNames = ['bottom', 'front', 'left', 'right', 'back', 'top']
sideSetNames = nodeSetNames

# Model dimension (default is 3)
numDim = model.dim

numNodes = model.nodeIds.size
numElems = model.elemIds.size
numNodeSets = 6
numSideSets = 6

# The number of blocks is equal to the unique numbers of block ids
blocks = model.blockIds
block_ids = np.unique(blocks)
numBlocks = len(block_ids)

exodusTitle = 'Converted from ' + filename + ' by em2ex.py'

coordNames = ["x", "y", "z"]
elemType = 'HEX8'
nodesPerElem = 8

# Write the exodus file using the exodus python API
exodusFile = exodus(filename_base + '.e',
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

exodusFile.put_node_id_map(np.arange(1, numNodes+1))
exodusFile.put_elem_id_map(np.arange(1, numElems+1))

exodusFile.put_elem_blk_names(block_ids.astype(str))

# Put all the element connectivities per block
for blkid in block_ids:
    numElemsInBlock = blocks[blocks==blkid].size
    exodusFile.put_elem_blk_info(blkid, elemType, numElemsInBlock, nodesPerElem, 0)
    exodusFile.put_elem_connectivity(blkid, model.elemNodes[blocks.flatten()==blkid].flatten())

for i in range(len(nodeSets)):
        exodusFile.put_node_set_params(i, len(nodeSets[i]))
        exodusFile.put_node_set(i, nodeSets[i])

if nodeSetNames:
    exodusFile.put_node_set_names(nodeSetNames)

for i in range(len(sideSets)):
        exodusFile.put_side_set_params(i, len(sideSets[i]),0)
        exodusFile.put_side_set(i, sideSets[i], sideSetSides[i])

if sideSetNames:
    exodusFile.put_side_set_names(nodeSetNames)

# Only want a single time step for this exodus file
exodusFile.put_time(1, 0)

# Add any elemental reservoir properties as elemental variables
if model.elemVars:
    exodusFile.set_element_variable_number(len(model.elemVars))

    var_counter = 1
    for var in model.elemVars:
        exodusFile.put_element_variable_name(var.lower(), var_counter)
        var_counter += 1

    for blkid in block_ids:
        for var in model.elemVars:
            exodusFile.put_element_variable_values(blkid, var.lower(), 1, model.elemVars[var])

    # Add elemental variables to sidesets as well
    exodusFile.set_side_set_variable_number(len(model.elemVars))

    var_counter = 1
    for var in model.elemVars:
        exodusFile.put_side_set_variable_name(var.lower(), var_counter)
        var_counter += 1

    for var in model.elemVars:
        for i in range(len(sideSets)):
            exodusFile.put_side_set_variable_values(i, var.lower(), 1, model.elemVars[var].take(np.asarray(sideSets[i]) - 1))

# Add any nodal variable values
if model.nodeVars:
    exodusFile.set_node_variable_number(len(model.nodeVars))

    var_counter = 1
    for var in model.nodeVars:
        exodusFile.put_node_variable_name(var.lower(), var_counter)
        var_counter += 1

    for var in model.nodeVars:
        exodusFile.put_node_variable_values(var.lower(), 1, model.nodeVars[var])

    # Add nodal variables to nodesets as well
    exodusFile.set_node_set_variable_number(len(model.nodeVars))

    var_counter = 1
    for var in model.nodeVars:
        exodusFile.put_node_set_variable_name(var.lower(), var_counter)
        var_counter += 1

    for var in model.nodeVars:
        for i in range(len(nodeSets)):
            exodusFile.put_node_set_variable_values(i, var.lower(), 1, model.nodeVars[var].take(np.asarray(nodeSets[i]) - 1))

# Finally, close the exodus file
exodusFile.close()
