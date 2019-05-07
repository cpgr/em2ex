#!/usr/bin/env python

# Convert reservoir Earth model to exodus mesh

import numpy as np
from readers import eclipse
from exodus import exodus
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

# Parse the input file and extract node coordinates, numbering and properties
if file_extension == '.grdecl':
    xcoords, ycoords, zcoords, nodeIds, elemIds, elemNodes, props = eclipse.parseEclipse(filename)

else:
    print 'File extension ', file_extension, ' not supported'
    exit()

# After parsing the reservoir model, and extracting the material properties, the Exodus
# file can be written once the data is correctly formatted

# Nodesets for the boundaries of the model
nodeSets = []
nodeSets.append(nodeIds[0,:,:].flatten().tolist())
nodeSets.append(nodeIds[:,0,:].flatten().tolist())
nodeSets.append(nodeIds[:,:,0].flatten().tolist())
nodeSets.append(nodeIds[:,:,-1].flatten().tolist())
nodeSets.append(nodeIds[:,-1,:].flatten().tolist())
nodeSets.append(nodeIds[-1,:,:].flatten().tolist())

# Sidesets for the boundaries of the model
sideSets = []
sideSets.append(elemIds[0,:,:].flatten().tolist())
sideSets.append(elemIds[:,0,:].flatten().tolist())
sideSets.append(elemIds[:,:,0].flatten().tolist())
sideSets.append(elemIds[:,:,-1].flatten().tolist())
sideSets.append(elemIds[:,-1,:].flatten().tolist())
sideSets.append(elemIds[-1:,:].flatten())

# Sideset side numbers
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

# Assumes that the model is always 3D
numDim = 3

numNodes = nodeIds.size
numElems = elemIds.size
numNodeSets = 6
numSideSets = 6

# Now prepare to write the exodus exodus file
# Block ids for the mesh
if 'SATNUM' in props:
    blocks = props['SATNUM']
else:
    blocks = np.zeros(numElems)

# The number of blocks is equal to the unique numbers of satnum values
block_ids = np.unique(props['SATNUM'])
# Not working properly, set a single block
blocks = np.zeros(numElems)
block_ids = [0]
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
exodusFile.put_coords(xcoords, ycoords, zcoords)

exodusFile.put_node_id_map(np.arange(1, numNodes+1))
exodusFile.put_elem_id_map(np.arange(1, numElems+1))

# Put all the element connectivities per block
for blkid in block_ids:
    numElemsInBlock = blocks[blocks==blkid].size
    exodusFile.put_elem_blk_info(blkid, elemType, numElemsInBlock, nodesPerElem, 0)
    exodusFile.put_elem_connectivity(blkid, elemNodes[blocks.flatten()==blkid].flatten())

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
exodusFile.put_time(1,0)

# Add the reservoir properties as elemental variables
num_props = len(props)
exodusFile.set_element_variable_number(num_props)

prop_counter = 1
for prop in props:
    exodusFile.put_element_variable_name(prop.lower(), prop_counter)
    prop_counter += 1

for blkid in block_ids:
    for prop in props:
        exodusFile.put_element_variable_values(blkid, prop.lower(), 1, props[prop])

exodusFile.close()
