# Functions to read Eclipse grdecl files and parse the input

import numpy as np
from exodus_model.ExodusModel import ExodusModel
from readers.reader_utils import *
import os

class EclipseData(object):
    '''Class containing data from an Eclipse file'''

    def __init__(self):
        self._specgrid = None
        self._mapaxes = None
        self._gridunit = None
        self._nx = None
        self._ny = None
        self._nz = None
        self._coord = None
        self._zcorn = None
        self._elemProps = {}

    # Grid size data from SPECGRID
    @property
    def specgrid(self):
        return self._specgrid

    @specgrid.setter
    def specgrid(self, spec):
        self._specgrid = spec

    # Map axes data from MAPAXES
    @property
    def mapaxes(self):
        return self._mapaxes

    @mapaxes.setter
    def mapaxes(self, axes):
        self._mapaxes = axes

    # Grid unit data from GRIDUNIT
    @property
    def gridunit(self):
        return self._gridunit

    @gridunit.setter
    def gridunit(self, grid):
        self._gridunit = grid

    # Number of elements
    @property
    def nx(self):
        assert self._specgrid, 'SPECGRID data must be loaded before getting nx'
        return int(self._specgrid[0])

    @property
    def ny(self):
        assert self._specgrid, 'SPECGRID data must be loaded before getting ny'
        return int(self._specgrid[1])

    @property
    def nz(self):
        assert self._specgrid, 'SPECGRID data must be loaded before getting nz'
        return int(self._specgrid[2])

    # Nodal coordinates in x and y directions
    @property
    def coord(self):
        return self._coord

    @coord.setter
    def coord(self, coords):
        self._coord = coords

    # Nodal corner coordinates in z direction
    @property
    def zcorn(self):
        return self._zcorn

    @zcorn.setter
    def zcorn(self, zcorn):
        self._zcorn = zcorn

    # Element properties
    @property
    def elemProps(self, prop = None):
        if not prop:
            return self._elemProps
        else:
            return self._elemProps[prop]

    @elemProps.setter
    def elemProps(self, prop, value = None):
        if not value:
            self._elemProps = prop
        else:
            self._elemProps[prop] = value

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

def readEclipse(f, eclipse):
    ''' Read an Eclipse grdecl file and store the data in an Eclipse object '''

    # Keywords that may be read in the Eclipse file
    ECLIPSE_KEYWORDS =  ['ACTNUM', 'SATNUM', 'PORO', 'PERMX', 'PERMY', 'PERMZ']

    # Open the .grdecl file for reading
    with open(f, 'r') as file:
        for line in file:

            if line.startswith('--') or  not line.strip():
                # Skip comments and blank lines
                continue

            elif line.startswith('SPECGRID'):
                eclipse.specgrid = next(file).split()

            elif line.startswith('MAPAXES'):
                eclipse.mapaxes = readBlock(file)

            elif line.startswith('GRIDUNIT'):
                eclipse.gridunit = next(file).split()
                eclipse.gridunit.pop()

            elif line.startswith('COORD') and 'COORDSYS' not in line:
                eclipse.coord = readBlock(file)

            elif line.startswith('ZCORN'):
                eclipse.zcorn = readBlock(file)

            elif line.startswith('INCLUDE'):
                include_file = next(file).split()[0]
                filepath = os.path.split(f)[0]
                readEclipse(os.path.join(filepath, include_file), eclipse)

            elif line.split()[0] in ECLIPSE_KEYWORDS:
                # Read in all properties known to the reader (in ECLIPSE_KEYWORDS)
                prop = line.split()[0]
                proplistname = prop.lower() + 'list'
                proplistname = np.asarray(readBlock(file))
                eclipse.elemProps[prop] = proplistname

            else:
                # Skip all unkown sections
                continue

    return


def parseEclipse(f, args):
    '''Parse the ECLIPSE file and return node coordinates and material properties'''

    # Eclipse data object
    eclipse = EclipseData()

    # Read the Eclipse grdecl file
    readEclipse(f, eclipse)

    # Check that required SPECGRID, COORD and ZCORN data has been supplied
    if not eclipse.specgrid:
        print("No SPECGRID data found in ", f)
        exit()

    if not eclipse.coord:
        print("No COORD data found in ", f)
        exit()

    if not eclipse.zcorn:
        print("No ZCORN data found in ", f)
        exit()

    # Check the optional MAPAXES data
    if args.use_mapaxes:
        if eclipse.mapaxes:
            if len(list(eclipse.mapaxes)) != 6:
                print("The number of MAPAXES entries read is not correct")
                exit()

        if eclipse.gridunit:
            if len(list(eclipse.gridunit)) > 2:
                print("The number of GRIDUNIT entries read is not correct")
                exit()

            # The second element is either MAP or blank - if blank make it GRID
            if len(list(eclipse.gridunit)) == 1:
                eclipse.gridunit.append("GRID")

    # The number of elements in the x, y and z directions
    nx = eclipse.nx
    ny = eclipse.ny
    nz = eclipse.nz

    # Check the number of COORD entries parsed is correct (6 points per entry)
    if (nx+1)*(ny+1)*6 != len(list(eclipse.coord)):
        print("The number of COORD entries read is not correct")
        exit()

    # Check the number of ZCORN entries parsed is correct
    if (2 * nx)*(2 * ny) *(2 * nz) != len(list(eclipse.zcorn)):
        print("The number of ZCORN entries read is not correct")
        exit()

    # Check all of the elemental properties that have been parsed
    for prop in eclipse.elemProps:
        if eclipse.elemProps[prop].size != nx * ny * nz:
            print("The number of " + prop + " entries read is not correct")
            exit()

    # Notify user that parsing has finished
    print("Finished parsing Eclipse file")

    # Now the data can be reshaped and processed for easy use
    # The COORD data has six entries for each of the (nx+1)*(ny+1) nodes
    coord = np.asarray(eclipse.coord).reshape(ny+1, nx+1, 6)

     # Transform the coordinates to MAPAXES coordinates if use_mapaxes is specified and
     # MAPAXES exists and GRIDUNIT exists and GRIDUNIT = GRID
    if args.use_mapaxes:

        if not eclipse.mapaxes:
            print("No MAPAXES keyword exists, so don't specify --mapaxes")
            exit()

        transform_coords = False
        if eclipse.gridunit:
            if eclipse.gridunit[1] == "GRID":
                transform_coords = True

        if transform_coords:
            # Origin and rotation vectors from MAPAXES
            xorigin, yorigin = eclipse.mapaxes[2], eclipse.mapaxes[3]
            xvec = np.array([eclipse.mapaxes[4] - xorigin, eclipse.mapaxes[5] - yorigin])
            yvec = np.array([eclipse.mapaxes[0] - xorigin, eclipse.mapaxes[1] - yorigin])

            # Normalise the rotation vectors
            xvec = xvec / np.sqrt(xvec[0]**2 + xvec[1]**2)
            yvec = yvec / np.sqrt(yvec[0]**2 + yvec[1]**2)

            # The x and y coordinates from COORD
            xdata = np.asarray(coord[:,:,0])
            ydata = np.asarray(coord[:,:,1])

            newx = xvec[0] * (xdata - xorigin) + xvec[1] * (ydata - yorigin)
            newy = yvec[0] * (xdata - xorigin) + yvec[1] * (ydata - yorigin)

            coord[:,:,0], coord[:,:,1] = newx, newy

    # Transform coord data to zcorn format (so that there is an x and y coordinate
    # for each node in the grid)
    xcorn, ycorn = coordToCorn(coord, nz)

    # The ZCORN data varies by x, y and then z. Reshape it into an array where
    # the first index gives the layer, the second the y coordinates and the third
    # the x coordinates
    zcorn = np.asarray(eclipse.zcorn).reshape(2*nz, 2*ny, 2*nx)

    # Flip the Z coordinates if specified
    if args.flip_z:
        zcorn = - zcorn

    # Now transform all of the coordinate arrays into element-ordered array, where
    # each row corresponds to a single element containing eight corners
    elemcornx = elemCornerCoords(xcorn)
    elemcorny = elemCornerCoords(ycorn)
    elemcornz = elemCornerCoords(zcorn)

    # Some elements may be inactive (ACTNUM = 0), so don't count them
    if 'ACTNUM' in eclipse.elemProps:
        active_elements = eclipse.elemProps['ACTNUM'].reshape(nz, ny, nx).astype(int)
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
    if 'SATNUM' in eclipse.elemProps:
        blocks = eclipse.elemProps['SATNUM'].astype(int).reshape((nz, ny, nx))
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

    # Remove any zeros (nodes start at 1)
    elemNodes = elemNodes[~np.any(elemNodes == 0, axis=1)]

    # Reorder elemNodes for correct ordering if flipped
    if args.flip_z:
        elemNodes = elemNodes[:, [4, 5, 6, 7, 0, 1, 2, 3]]

    # Remove elemental properties in inactive elements
    for prop in eclipse.elemProps:
        eclipse.elemProps[prop] = eclipse.elemProps[prop][active_elements.flatten() > 0]

    # Add data to the ExodusModel object
    model = ExodusModel()
    model.xcoords = xcoords
    model.ycoords = ycoords
    model.zcoords = zcoords
    model.nodeIds = nodeIds
    model.elemIds = elemIds
    model.elemNodes = elemNodes
    model.elemVars = eclipse.elemProps
    model.numElems = num_active_elements
    model.numNodes = num_active_nodes
    model.blockIds = blocks.flatten()[active_elements.flatten()>0]

    # Add sidesets if required
    if args.omit_sidesets:
        model.numSideSets = 0
    else:
        addSideSets(model)

        # And flip the top and bottom ids if mesh is flipped
        if args.flip_z:
            model.sideSetSides[0], model.sideSetSides[5] = model.sideSetSides[5], model.sideSetSides[0]
            model.sideSetNames[0], model.sideSetNames[5] = model.sideSetNames[5], model.sideSetNames[0]

    # Add nodesets if required
    if args.omit_nodesets:
        model.numNodeSets = 0
    else:
        addNodeSets(model)

        # And flip the top and bottom ids if mesh is flipped
        if args.flip_z:
            model.nodeSetNames[0], model.nodeSetNames[5] = model.nodeSetNames[5], model.nodeSetNames[0]

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
