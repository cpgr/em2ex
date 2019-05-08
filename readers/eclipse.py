# Functions to read Eclipse grdecl files and parse the input

import numpy as np
from ExodusModel import ExodusModel
from nodeutils import addNode

def readBlock(f):
    '''Reads block of data and returns it as a list'''
    block = []
    while True:
        line = next(f)
        # Skip comments
        if line.startswith('--'):
            continue
        data = processData(line)
        block.extend(data)
        # End read if line ends with /
        if block[-1] == '/':
            block.pop()
            block = map(float, block)
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

def parseEclipse(f):
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
        print "No SPECGRID data found in ", f
        exit()

    if not coordlist:
        print "No COORD data found in ", f
        exit()

    if not zcornlist:
        print "No ZCORN data found in ", f
        exit()

    # The number of elements in the x, y and z directions are specified in the SPECGRID data
    nx = int(specgridlist[0])
    ny = int(specgridlist[1])
    nz = int(specgridlist[2])

    # Check the number of COORD entries parsed is correct (6 points per entry)
    if (nx+1)*(ny+1)*6 != len(coordlist):
        print "The number of COORD entries read is not correct"
        exit()

    # Check the number of ZCORN entries parsed is correct
    if (2 * nx)*(2 * ny) *(2 * nz) != len(zcornlist):
        print "The number of ZCORN entries read is not correct"
        exit()

    # Check all of the elemental properties that have been parsed
    for prop in elemProps:
        if len(elemProps[prop]) != nx*ny*nz:
            print "The number of", prop, "entries read is not correct"
            exit()

    # Notify user that parsing has finished
    print "Finished parsing Eclipse file"

    # Now the data can be reshaped and processed for easy use
    # The COORD data has six entries for each of the (nx+1)*(ny+1) nodes
    coord = np.asarray(coordlist).reshape(ny+1, nx+1,6)

    # The ZCORN data varies by x, y and then z. Reshape it into an array where the first index gives the layer, the second the y coordinates and the third the x coordinates
    zcorn = np.asarray(zcornlist).reshape(2*nz, 2*ny, 2*nx)
    # Also make sure that zcorn is in increasing z order
    zcorn.sort(axis=0)

    # The x and y data are taken from the COORD data. These are repeated nz+1 times. The z data is taken
    # from the ZCORN data, noting that it is repeated for each internal corner.
    xdata = np.asarray([coord[:,:,0]] * (nz+1))
    ydata = np.asarray([coord[:,:,1]] * (nz+1))
    zdata = np.pad(zcorn, ((0,1), (0,1), (0,1)),'edge')[::2,::2,::2]

    # Loop through the elements and add the node numbers following the right-hand rule,
    # starting at 1. Also construct the element connectivity array
    nodeIds = np.zeros((nz+1, ny+1, nx+1), dtype=int)
    elemNodes = np.zeros((nz*ny*nx, 8), dtype=int)
    elemIds = np.zeros((nz, ny, nx), dtype=int)

    nodenum = 1
    elemnum = 0
    for k in xrange(0,nz):
        for j in xrange(0,ny):
            for i in xrange(0,nx):
                # Label all the nodes for this element
                nodenum = addNode(nodeIds, i, j, k, nodenum)
                nodenum = addNode(nodeIds, i+1, j, k, nodenum)
                nodenum = addNode(nodeIds, i+1, j+1, k, nodenum)
                nodenum = addNode(nodeIds, i, j+1, k, nodenum)
                nodenum = addNode(nodeIds, i, j, k+1, nodenum)
                nodenum = addNode(nodeIds, i+1, j, k+1, nodenum)
                nodenum = addNode(nodeIds, i+1, j+1, k+1, nodenum)
                nodenum = addNode(nodeIds, i, j+1, k+1, nodenum)

    for k in xrange(0,nz):
        for j in xrange(0,ny):
            for i in xrange(0,nx):
                # Add the nodes for this element to the connectivity array
                elemNodes[elemnum, 0] = nodeIds[k, j, i]
                elemNodes[elemnum, 1] = nodeIds[k, j, i+1]
                elemNodes[elemnum, 2] = nodeIds[k, j+1, i+1]
                elemNodes[elemnum, 3] = nodeIds[k, j+1, i]
                elemNodes[elemnum, 4] = nodeIds[k+1, j, i]
                elemNodes[elemnum, 5] = nodeIds[k+1, j, i+1]
                elemNodes[elemnum, 6] = nodeIds[k+1, j+1, i+1]
                elemNodes[elemnum, 7] = nodeIds[k+1, j+1, i]

                # Also the array of element ids
                elemIds[k,j,i] = elemnum + 1
                elemnum+=1

    # Order the coordinates according to the node numbering
    xcoords = np.zeros(((nx +1) * (ny+1) * (nz+1)))
    ycoords = np.zeros(((nx +1) * (ny+1) * (nz+1)))
    zcoords = np.zeros(((nx +1) * (ny+1) * (nz+1)))

    for k in xrange(0,nz+1):
        for j in xrange(0,ny+1):
            for i in xrange(0,nx+1):
                # Get the node number corresponding to i,j,k
                # Note that the array position is node_id - 1
                nid = nodeIds[k,j,i]
                xcoords[nid-1] = xdata[k,j,i]
                ycoords[nid-1] = ydata[k,j,i]
                zcoords[nid-1] = zdata[k,j,i]

    # Add data to the ExodusModel object
    model = ExodusModel()
    model.nx = nx
    model.ny = ny
    model.nz = nz
    model.xcoords = xcoords
    model.ycoords = ycoords
    model.zcoords = zcoords
    model.nodeIds = nodeIds
    model.elemIds = elemIds
    model.elemNodes = elemNodes
    model.elemVars = elemProps

    # The number of blocks is equal to the unique numbers of satnum values
    # Block ids for the mesh
    if 'SATNUM' in model.elemVars:
        model.blockIds = model.elemVars['SATNUM'].astype(int)
    else:
        model.blockIds = np.zeros(numElems).astype(int)

    return model
