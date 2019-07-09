# Functions to read Eclipse grdecl files and parse the input

import numpy as np
from exodus_model.ExodusModel import ExodusModel
from readers.reader_utils import *

def readBlock(f):
    '''Reads block of data and returns it as a list'''
    block = []
    while True:
        line = next(f)
        # Skip comments and blank lines
        if line.startswith('--') or not line.strip():
            continue
        data = processData(line)
        block.extend(data)
        # End read if line ends with /
        if block[-1] == '/':
            block.pop()
            block = list(map(float, block))
            break
    return block

def processData(line):
    '''Expands shorthand notation N*data to N copies of data'''
    data = []
    for t in line.split():
        if t.find('*') == -1:
            data.append(t)
        else:
            tmp = t.split('*')
            expanded = [tmp[1]] * int(tmp[0])
            data.extend(expanded)
    return data

def readKeyword(f, keyword):
    '''Read keyword data from grdecl file'''
    for line in f:
        # Skip comments and blank lines
        if line.startswith('--') or not line.strip():
            continue

        elif line.startswith(keyword):
            block = readBlock(f)

        else:
            # Skip all unknown sections
            continue

    return block

def parseEclipse(f, args):
    '''Parse the ECLIPSE file and return node coordinates and material properties'''

    # Keywords that may be read in the Eclipse file
    ECLIPSE_KEYWORDS =  ['ACTNUM', 'SATNUM', 'PORO', 'PERMX', 'PERMY', 'PERMZ']

    # Open the .grdecl file for reading
    file = open(f)

    # Dict for storing elemental (cell-centred) reservoir properties
    elemProps = {};

    # Declare empty lists for all required keywords
    specgridlist = []
    coordlist = []
    zcornlist = []

    for line in file:

        if line.startswith('--') or  not line.strip():
            # Skip comments and blank lines
            continue

        elif line.startswith('SPECGRID'):
            specgridlist = next(file).split()

        elif line.startswith('COORD') and 'COORDSYS' not in line:
            coordlist = readBlock(file)

        elif line.startswith('ZCORN'):
            zcornlist = readBlock(file)

        elif line.split()[0] in ECLIPSE_KEYWORDS:
            # Read in all properties known to the reader (in ECLIPSE_KEYWORDS)
            prop = line.split()[0]
            proplistname = prop.lower() + 'list'
            proplistname = np.asarray(readBlock(file))
            elemProps[prop] = proplistname

        else:
            # Skip all unkown sections
            continue

    # Close the file after parsing
    file.close()

    # Check that required SPECGRID, COORD and ZCORN data has been supplied
    if not specgridlist:
        print("No SPECGRID data found in ", f)
        exit()

    if not coordlist:
        print("No COORD data found in ", f)
        exit()

    if not zcornlist:
        print("No ZCORN data found in ", f)
        exit()

    # The number of elements in the x, y and z directions are specified in the
    # SPECGRID data
    nx = int(specgridlist[0])
    ny = int(specgridlist[1])
    nz = int(specgridlist[2])

    # Check the number of COORD entries parsed is correct (6 points per entry)
    if (nx+1)*(ny+1)*6 != len(list(coordlist)):
        print("The number of COORD entries read is not correct")
        exit()

    # Check the number of ZCORN entries parsed is correct
    if (2 * nx)*(2 * ny) *(2 * nz) != len(list(zcornlist)):
        print("The number of ZCORN entries read is not correct")
        exit()

    # Check all of the elemental properties that have been parsed
    for prop in elemProps:
        if elemProps[prop].size != nx*ny*nz:
            print("The number of " + prop + " entries read is not correct")
            exit()

    # Notify user that parsing has finished
    print("Finished parsing Eclipse file")

    # Now the data can be reshaped and processed for easy use
    # The COORD data has six entries for each of the (nx+1)*(ny+1) nodes
    coord = np.asarray(coordlist).reshape(ny+1, nx+1, 6)

    # Transform coord data to zcorn format (so that there is an x and y coordinate
    # for each node in the grid)
    xcorn, ycorn = coordToCorn(coord, nz)

    # The ZCORN data varies by x, y and then z. Reshape it into an array where
    # the first index gives the layer, the second the y coordinates and the third
    # the x coordinates
    zcorn = np.asarray(zcornlist).reshape(2*nz, 2*ny, 2*nx)
    # Also make sure that zcorn is in increasing z order
    zcorn.sort(axis=0)

    # Now transform all of the coordinate arrays into element-ordered array, where
    # each row corresponds to a single element containing eight corners
    elemcornx = elemCornerCoords(xcorn)
    elemcorny = elemCornerCoords(ycorn)
    elemcornz = elemCornerCoords(zcorn)

    # Some elements may be inactive (ACTNUM = 0), so don't count them
    if 'ACTNUM' in elemProps:
        active_elements = elemProps['ACTNUM'].reshape(nz, ny, nx).astype(int)
    else:
        # All elements are active
        active_elements = np.ones((nz, ny, nx), dtype = int)

    # The number of active elements is
    num_active_elements = np.count_nonzero(active_elements)

    # Generate the connection data by numbering all unique nodes in the mesh
    elemNodes = numberNodesInElems(elemcornz, active_elements)

    # Construct the nodeIds for all corners in all elements
    nodeIds = np.zeros((2*nz, 2*ny,2*nx))

    for k in range(0, nz):
        for j in range(0, ny):
            for i in range(0, nx):
                if active_elements[k, j, i]:
                    nodeIds[2*k, 2*j, 2*i] = elemNodes[k, j, i, 0]
                    nodeIds[2*k, 2*j, 2*i + 1] = elemNodes[k, j, i, 1]
                    nodeIds[2*k, 2*j + 1, 2*i] = elemNodes[k, j, i, 3]
                    nodeIds[2*k, 2*j + 1, 2*i + 1] = elemNodes[k, j, i, 2]
                    nodeIds[2*k + 1, 2*j, 2*i] = elemNodes[k, j, i, 4]
                    nodeIds[2*k + 1, 2*j, 2*i + 1] = elemNodes[k, j, i, 5]
                    nodeIds[2*k + 1, 2*j + 1, 2*i] = elemNodes[k, j, i, 7]
                    nodeIds[2*k + 1, 2*j + 1, 2*i + 1] = elemNodes[k, j, i, 6]

    # The number of active nodes is
    num_active_nodes = np.max(nodeIds).astype(int)

    # Also require the element ids for setting the sidesets. Note that the internal
    # exodus element numbering is for each block in turn (ie. all elements in block 1
    # are numbered consecutively, then all elements in the next block, etc.)

    # Block IDs (needed to provide correct element numbering)
    if 'SATNUM' in elemProps:
        blocks = elemProps['SATNUM'].astype(int).reshape((nz, ny, nx))
    else:
        blocks = np.zeros((nz, ny, nx), dtype=int)

    # Give each element an ID (from 1 to num_active_elements)
    elemIds = np.zeros((nz, ny, nx), dtype=int)
    elemnum = 1
    for blkid in np.unique(blocks):
        for k in range(0,nz):
            for j in range(0,ny):
                for i in range(0,nx):
                    # Only consider active elements
                    if active_elements[k, j, i]:
                        if blocks[k, j, i] == blkid:
                            elemIds[k,j,i] = elemnum
                            elemnum+=1

    # Order the coordinates according to the node numbering
    elemNodes = elemNodes.reshape(nz*ny*nx, 8)

    xcoords = elemCornToCoord(elemcornx, elemNodes)
    ycoords = elemCornToCoord(elemcorny, elemNodes)
    zcoords = elemCornToCoord(elemcornz, elemNodes)

    # Flip the Z coordinates if specified
    if args.flip_z:
        zcoords = - zcoords

    # Remove any zeros (nodes start at 1)
    elemNodes = elemNodes[~np.any(elemNodes == 0, axis=1)]

    # Remove elemental properties in inactive elements
    for prop in elemProps:
        elemProps[prop] = elemProps[prop][active_elements.flatten() > 0]

    # Add data to the ExodusModel object
    model = ExodusModel()
    model.xcoords = xcoords
    model.ycoords = ycoords
    model.zcoords = zcoords
    model.nodeIds = nodeIds
    model.elemIds = elemIds
    model.elemNodes = elemNodes
    model.elemVars = elemProps
    model.numElems = num_active_elements
    model.numNodes = num_active_nodes
    model.blockIds = blocks.flatten()[active_elements.flatten()>0]

    # Add sidesets if required
    if args.omit_sidesets:
        model.numSideSets = 0
    else:
        addSideSets(model)

    # Add nodesets if required
    if args.omit_nodesets:
        model.numNodeSets = 0
    else:
        addNodeSets(model)

    return model

def elemCornerCoords(corner_coords):
    ''' Returns coordinates for all eight corner of each element '''

    # Each corner_coords array is twice the number of elements in each direction
    dnz, dny, dnx = corner_coords.shape
    numelems = int((dnx * dny * dnz) / 8)
    elemCorns = np.zeros((numelems, 8))

    elemcounter = 0;
    for k in range(0, dnz, 2):
        for j in range(0, dny, 2):
            for i in range(0, dnx, 2):
                elemCorns[elemcounter, 0] = corner_coords[k, j, i]
                elemCorns[elemcounter, 1] = corner_coords[k, j, i+1]
                elemCorns[elemcounter, 2] = corner_coords[k, j+1, i+1]
                elemCorns[elemcounter, 3] = corner_coords[k, j+1, i]
                elemCorns[elemcounter, 4] = corner_coords[k+1, j, i]
                elemCorns[elemcounter, 5] = corner_coords[k+1, j, i+1]
                elemCorns[elemcounter, 6] = corner_coords[k+1, j+1, i+1]
                elemCorns[elemcounter, 7] = corner_coords[k+1, j+1, i]
                elemcounter += 1

    return elemCorns

def coordToCorn(coord, nz):
    ''' Transform coord data (x, y) coordinates to (x, y) corners for each node '''

    # Extract x and y coordinates from coord data
    xdata = np.asarray(coord[:,:,0])
    ydata = np.asarray(coord[:,:,1])

    # Repeat all internal coordinates to double the size of the arrays
    xcorn = np.repeat(np.repeat(xdata, 2, axis=0), 2, axis=1)[1:-1,1:-1]
    ycorn = np.repeat(np.repeat(ydata, 2, axis=0), 2, axis=1)[1:-1,1:-1]

    # Repeat each row 2 nz times
    xcorn = np.array([xcorn] * 2 * nz)
    ycorn = np.array([ycorn] * 2 * nz)

    return xcorn, ycorn

def elemCornToCoord(elemcorns, elemNodes):
    ''' Transform coordinate data for each element corner to a unique node ordered
    list of coordinates '''

    nodes, idx = np.unique(elemNodes, return_index=True)
    coords = elemcorns.flatten()[idx][np.nonzero(elemNodes.flatten()[idx])]

    return coords

def numberNodesInElems(elemcornz, active_elements):
    ''' Number all unique nodes in grid including fault check'''

    nz, ny, nx = active_elements.shape
    elemcornz = elemcornz.reshape(nz, ny, nx, 8)
    elemNodes = np.zeros((nz, ny, nx, 8), dtype=int)

    nodenum = 1

    # The following iterates over all elements, and checks if all corner nodes are unique
    # or if they coincide with any previously visited elements. Only nodes that
    # haven't been seen before are numbered. Importantly, after numbering a node any
    # coincident nodes in inactive elements are also renumbered.

    for k in range(0, nz):
        for j in range(0, ny):
            for i in range(0, nx):
                if active_elements[k, j, i]:
                    # Node 1
                    if k > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k - 1, j, i, 4]) and elemNodes[k - 1, j, i, 4] != 0:
                        elemNodes[k, j, i, 0] = elemNodes[k - 1, j, i, 4]
                    elif j > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k, j - 1, i, 3]) and elemNodes[k, j - 1, i, 3] != 0:
                        elemNodes[k, j, i, 0] = elemNodes[k, j - 1, i, 3]
                    elif i > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k, j, i - 1, 1]) and elemNodes[k, j, i - 1, 1] != 0:
                        elemNodes[k, j, i, 0] = elemNodes[k, j, i - 1, 1]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 0] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if k > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k - 1, j, i, 4]) and elemNodes[k - 1, j, i, 4] == 0:
                            elemNodes[k - 1, j, i, 4] = elemNodes[k, j, i, 0]
                        elif j > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k, j - 1, i, 3]) and elemNodes[k, j - 1, i, 3] == 0:
                            elemNodes[k, j - 1, i, 3] = elemNodes[k, j, i, 0]
                        elif i > 0 and np.isclose(elemcornz[k, j, i, 0], elemcornz[k, j, i - 1, 1]) and elemNodes[k, j, i - 1, 1] == 0:
                            elemNodes[k, j, i - 1, 1] = elemNodes[k, j, i, 0]

                    # Node 2
                    if k > 0 and np.isclose(elemcornz[k, j, i, 1], elemcornz[k - 1, j, i, 5]) and elemNodes[k - 1, j, i, 5] != 0:
                        elemNodes[k, j, i, 1] = elemNodes[k - 1, j, i, 5]
                    elif j > 0 and np.isclose(elemcornz[k, j, i, 1], elemcornz[k, j - 1, i, 2]) and elemNodes[k, j - 1, i, 2] != 0:
                        elemNodes[k, j, i, 1] = elemNodes[k, j - 1, i, 2]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 1] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if k > 0 and np.isclose(elemcornz[k, j, i, 1], elemcornz[k - 1, j, i, 5]) and elemNodes[k - 1, j, i, 5] == 0:
                            elemNodes[k - 1, j, i, 5] = elemNodes[k, j, i, 1]
                        elif j > 0 and np.isclose(elemcornz[k, j, i, 1], elemcornz[k, j - 1, i, 2]) and elemNodes[k, j - 1, i, 2] == 0:
                            elemNodes[k, j - 1, i, 2] = elemNodes[k, j, i, 1]

                    # Node 3
                    if k > 0 and np.isclose(elemcornz[k, j, i, 2], elemcornz[k - 1, j, i, 6]) and elemNodes[k - 1, j, i, 6] != 0:
                        elemNodes[k, j, i, 2] = elemNodes[k - 1, j, i, 6]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 2] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if k > 0 and np.isclose(elemcornz[k, j, i, 2], elemcornz[k - 1, j, i, 6]) and elemNodes[k - 1, j, i, 6] == 0:
                            elemNodes[k - 1, j, i, 6] = elemNodes[k, j, i, 2]

                    # Node 4
                    if k > 0 and np.isclose(elemcornz[k, j, i, 3], elemcornz[k - 1, j, i, 7]) and elemNodes[k - 1, j, i, 7] != 0:
                        elemNodes[k, j, i, 3] = elemNodes[k - 1, j, i, 7]
                    elif i > 0 and np.isclose(elemcornz[k, j, i, 3], elemcornz[k, j, i - 1, 2]) and elemNodes[k, j, i - 1, 2] != 0 :
                        elemNodes[k, j, i, 3] = elemNodes[k, j, i - 1, 2]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 3] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if k > 0 and np.isclose(elemcornz[k, j, i, 3], elemcornz[k - 1, j, i, 7]) and elemNodes[k - 1, j, i, 7] == 0:
                            elemNodes[k - 1, j, i, 7] = elemNodes[k, j, i, 3]
                        elif i > 0 and np.isclose(elemcornz[k, j, i, 3], elemcornz[k, j, i - 1, 2]) and elemNodes[k, j, i - 1, 2] == 0 :
                            elemNodes[k, j, i - 1, 2] = elemNodes[k, j, i, 3]

                    # Node 5
                    if j > 0 and np.isclose(elemcornz[k, j, i, 4], elemcornz[k, j - 1, i, 7]) and elemNodes[k, j - 1, i, 7] != 0:
                        elemNodes[k, j, i, 4] = elemNodes[k, j - 1, i, 7]
                    elif i > 0 and np.isclose(elemcornz[k, j, i, 4], elemcornz[k, j, i - 1, 5]) and elemNodes[k, j, i - 1, 5] != 0:
                        elemNodes[k, j, i, 4] = elemNodes[k, j, i - 1, 5]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 4] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if j > 0 and np.isclose(elemcornz[k, j, i, 4], elemcornz[k, j - 1, i, 7]) and elemNodes[k, j - 1, i, 7] == 0:
                            elemNodes[k, j - 1, i, 7] = elemNodes[k, j, i, 4]
                        elif i > 0 and np.isclose(elemcornz[k, j, i, 4], elemcornz[k, j, i - 1, 5]) and elemNodes[k, j, i - 1, 5] == 0:
                            elemNodes[k, j, i - 1, 5] = elemNodes[k, j, i, 4]

                    # Node 6
                    if j > 0 and np.isclose(elemcornz[k, j, i, 5], elemcornz[k, j - 1, i, 6]) and elemNodes[k, j - 1, i, 6] != 0:
                        elemNodes[k, j, i, 5] = elemNodes[k, j - 1, i, 6]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 5] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if j > 0 and np.isclose(elemcornz[k, j, i, 5], elemcornz[k, j - 1, i, 6]) and elemNodes[k, j - 1, i, 6] == 0:
                            elemNodes[k, j - 1, i, 6] = elemNodes[k, j, i, 5]

                    # Node 7
                    elemNodes[k, j, i, 6] = nodenum; nodenum +=1;

                    # Node 8
                    if i > 0 and np.isclose(elemcornz[k, j, i, 7], elemcornz[k, j, i - 1, 6]) and elemNodes[k, j, i - 1, 6] != 0:
                        elemNodes[k, j, i, 7] = elemNodes[k, j, i - 1, 6]
                    else:
                        # Add a new node number
                        elemNodes[k, j, i, 7] = nodenum; nodenum +=1;
                        # Also check backwards to duplicate node if previous cell was inactive
                        if i > 0 and np.isclose(elemcornz[k, j, i, 7], elemcornz[k, j, i - 1, 6]) and elemNodes[k, j, i - 1, 6] == 0:
                            elemNodes[k, j, i - 1, 6] = elemNodes[k, j, i, 7]

    return elemNodes
