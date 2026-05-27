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

# Per-cell scalar property keywords the reader recognises out of the box.
# Any additional keywords (e.g. PVTNUM, EQLNUM, FIPNUM) can be passed by the
# caller via the `extra_keywords` argument to readEclipse (wired to the CLI
# flag --extra-keywords).
DEFAULT_KEYWORDS = ('ACTNUM', 'SATNUM', 'PORO',
                    'PERMX', 'PERMY', 'PERMZ',
                    'NTG', 'HEATCR', 'THCONR')

# Recognised length units for the GRIDUNIT keyword and the factor that
# converts them to metres. Files that omit GRIDUNIT default to METRES.
GRIDUNIT_TO_METRES = {
    'METRES': 1.0,
    'FEET':   0.3048,
    'CM':     0.01,
}

def readEclipse(f, eclipse, extra_keywords=()):
    ''' Read an Eclipse grdecl file and store the data in an Eclipse object.
    `extra_keywords` is an iterable of additional uppercase keyword names to
    read as per-cell properties on top of DEFAULT_KEYWORDS. '''

    keywords = set(DEFAULT_KEYWORDS) | {k.upper() for k in extra_keywords}

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
                # Eclipse string keywords are conventionally written with
                # single quotes (e.g. 'METRES' 'MAP' /). Strip the quotes so
                # downstream comparisons against bare values like 'METRES' or
                # 'GRID' work whether the file quotes the strings or not.
                tokens = next(file).split()
                tokens.pop()   # drop the trailing '/'
                eclipse.gridunit = [t.strip("'\"") for t in tokens]

            elif line.startswith('COORD') and 'COORDSYS' not in line:
                eclipse.coord = readBlock(file)

            elif line.startswith('ZCORN'):
                eclipse.zcorn = readBlock(file)

            elif line.startswith('INCLUDE'):
                include_file = next(file).split()[0]
                filepath = os.path.split(f)[0]
                readEclipse(os.path.join(filepath, include_file), eclipse,
                            extra_keywords=extra_keywords)

            elif line.split()[0] in keywords:
                # Read in all per-cell property arrays whose keyword is recognised
                prop = line.split()[0]
                eclipse.elemProps[prop] = np.asarray(readBlock(file))

            else:
                # Skip all unknown sections
                continue

    return


def parseEclipse(f, args):
    '''Parse the ECLIPSE file and return node coordinates and material properties'''

    # Eclipse data object
    eclipse = EclipseData()

    # Read the Eclipse grdecl file (with any user-supplied extra property keywords)
    extra_keywords = getattr(args, 'extra_keywords', None) or ()
    readEclipse(f, eclipse, extra_keywords=extra_keywords)

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

    # Surface typos: any --extra-keywords value the file (or its INCLUDEs)
    # never provided. Reported all at once so the user fixes them in one go.
    missing = [k for k in extra_keywords if k not in eclipse.elemProps]
    if missing:
        print("--extra-keywords requested {} but the keyword was not found in {}".format(
            ', '.join(missing), f))
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

    # Determine the grid's length unit from GRIDUNIT (default METRES if absent).
    # Print an info note for any recognised non-METRES unit so the user is aware,
    # plus a hint about --convert-to-m if they want the output in SI.
    grid_unit = (eclipse.gridunit[0].upper() if eclipse.gridunit else 'METRES')
    needs_conversion = grid_unit != 'METRES'
    unit_known = grid_unit in GRIDUNIT_TO_METRES
    if needs_conversion and unit_known:
        print("Note: input grid uses {} (from GRIDUNIT keyword). Output mesh will be in {}.".format(grid_unit, grid_unit))
        print("      Pass --convert-to-m to convert to metres on output.")
    elif needs_conversion and not unit_known:
        print("Note: input grid declares GRIDUNIT {} which is not recognised.".format(grid_unit))
        print("      Conversion to metres is not available; output mesh will use the input values.")

    # Validate the user's --convert-to-m request up front (before any work).
    do_convert = bool(getattr(args, 'convert_to_m', False)) and needs_conversion
    if getattr(args, 'convert_to_m', False) and needs_conversion and not unit_known:
        print("--convert-to-m: unrecognised GRIDUNIT value {!r}; cannot convert.".format(grid_unit))
        exit()

    # Now the data can be reshaped and processed for easy use
    # The COORD data has six entries for each of the (nx+1)*(ny+1) nodes
    coord = np.asarray(eclipse.coord).reshape(ny+1, nx+1, 6)

    # Reshape ZCORN early so subsetting (--extract-*) can slice it. The reshape
    # is independent of any later coord transforms (flip / translate / mapaxes /
    # flip_z), all of which leave the (k, j, i) cell indexing unchanged.
    zcorn = np.asarray(eclipse.zcorn).reshape(2*nz, 2*ny, 2*nx)

    # Apply --convert-to-m if requested: rescale every length-valued array by
    # the GRIDUNIT->metres factor. coord stores x/y/z for both pillar
    # endpoints (all 6 entries are coordinates); zcorn stores z values only.
    # Done here, before extract/refine/flip, so the rest of the pipeline
    # operates in metres.
    if do_convert:
        factor = GRIDUNIT_TO_METRES[grid_unit]
        coord = coord * factor
        zcorn = zcorn * factor
        print("Converted {} -> metres on output (factor {}).".format(grid_unit, factor))

    # Apply --extract-i/-j/-k subsetting if requested. Indices are 1-based
    # inclusive in file order (matching the cells as they appear in the
    # grdecl SPECGRID / properties sections), and the slice happens before
    # any flip / translate / mapaxes / refine so the user never has to think
    # about coordinate-system normalisation. See README for the flip caveat.
    extract_i = getattr(args, 'extract_i', None)
    extract_j = getattr(args, 'extract_j', None)
    extract_k = getattr(args, 'extract_k', None)
    if extract_i or extract_j or extract_k:
        i_lo, i_hi = _resolve_extract_range(extract_i, nx, 'i')
        j_lo, j_hi = _resolve_extract_range(extract_j, ny, 'j')
        k_lo, k_hi = _resolve_extract_range(extract_k, nz, 'k')
        coord, zcorn, eclipse.elemProps, nx, ny, nz = extractSubgrid(
            coord, zcorn, eclipse.elemProps, nx, ny, nz,
            i_lo, i_hi, j_lo, j_hi, k_lo, k_hi)

    # The exodus node numbering relies on a right-hand coordinate system, with
    # x and y increasing. However, eclipse can output a grid with a left-hand
    # coordinate system, with either (or both) x and y decreasing (ie, pointing in
    # the negative direction). This will lead to a negative element Jacobian when an
    # exodus mesh is created. Therefore, we flip the decreasing coordinate, create
    # the grid, then flip the coordinate again.

    flip_x, flip_y = False, False
    if (coord[:,:,0][0,-1] - coord[:,:,0][0,0] < 0):
        # x coordinates are in decreasing order — reverse all pillar data along column axis
        coord = coord[:, ::-1, :]
        flip_x = True

    if (coord[:,:,1][-1,0] - coord[:,:,1][0,0] < 0):
        # y coordinates are in decreasing order — reverse all pillar data along row axis
        coord = coord[::-1, :, :]
        flip_y = True

    # Translate the coordinates if the translate commandline option is specified
    if args.translate:
        for xi, yi in [(0, 1), (3, 4)]:
            coord[:,:,xi] = coord[:,:,xi] + args.translate[0]
            coord[:,:,yi] = coord[:,:,yi] + args.translate[1]

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
            # Origin and axis unit vectors from MAPAXES
            xorigin, yorigin = eclipse.mapaxes[2], eclipse.mapaxes[3]
            xvec = np.array([eclipse.mapaxes[4] - xorigin, eclipse.mapaxes[5] - yorigin])
            yvec = np.array([eclipse.mapaxes[0] - xorigin, eclipse.mapaxes[1] - yorigin])

            xvec = xvec / np.sqrt(xvec[0]**2 + xvec[1]**2)
            yvec = yvec / np.sqrt(yvec[0]**2 + yvec[1]**2)

            # Transform top and bottom pillar x,y: world = origin + local_x*xhat + local_y*yhat
            for xi, yi in [(0, 1), (3, 4)]:
                xdata = coord[:,:,xi].copy()
                ydata = coord[:,:,yi].copy()
                coord[:,:,xi] = xorigin + xdata * xvec[0] + ydata * yvec[0]
                coord[:,:,yi] = yorigin + xdata * xvec[1] + ydata * yvec[1]

    # Flip the Z coordinates if specified
    if args.flip_z:
        zcorn = - zcorn

    # Apply lateral (x, y) refinement if requested. Pillars are linearly
    # interpolated; per-cell tops and bottoms are bilinearly interpolated within
    # each parent (which preserves faults); element properties are inherited by
    # all child cells of each parent.
    if getattr(args, 'refine_xy', None):
        rx, ry = args.refine_xy
        coord, zcorn, eclipse.elemProps, nx, ny = refineLaterally(
            coord, zcorn, eclipse.elemProps, nx, ny, nz, rx, ry)

    # Transform coord data to zcorn format (so that there is an x and y coordinate
    # for each node in the grid)
    xcorn, ycorn = coordToCorn(coord, nz)

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

    # If pinched or distorted elements are removed, these elements will also be set to
    # be inactive.
    # Check for pinched out elements (where the vertical distance between nodes is less than tol)
    if args.no_pinch:
        distorted = distortedElem(elemcornx, elemcorny, elemcornz, args.pinch_tol).reshape(nz, ny, nx)
        active_elements[distorted] = 0

    # The number of active elements is
    num_active_elements = np.count_nonzero(active_elements)

    # Generate the connection data by numbering all unique nodes in the mesh
    elemNodes = numberNodesInElems(elemcornz, active_elements)

    # Construct the nodeIds for all corners in all elements. Inactive cells
    # contribute zeros (no node IDs written), matching the per-cell loop's
    # behaviour. Permute the per-cell corner axis into (kk, jj, ii) flat order,
    # zero inactive cells, then interleave the (kk, jj, ii) sub-axis into
    # (2*nz, 2*ny, 2*nx).
    permuted = np.zeros_like(elemNodes)
    permuted[..., _CORNER_TO_KJI] = elemNodes
    permuted *= active_elements.astype(bool)[..., None]
    nodeIds = (permuted.reshape(nz, ny, nx, 2, 2, 2)
                       .transpose(0, 3, 1, 4, 2, 5)
                       .reshape(2 * nz, 2 * ny, 2 * nx)
                       .astype(float))

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

    # Give each active element an ID from 1 to num_active_elements. Numbering
    # walks block IDs in ascending order (matching np.unique(blocks)); within
    # each block, cells are visited in (k, j, i) C-order. A stable sort by
    # block ID preserves that within-block order, and a cumulative count over
    # the sorted active mask assigns the sequential IDs in one pass.
    flat_blocks = blocks.flatten()
    flat_active = active_elements.flatten() > 0
    order = np.argsort(flat_blocks, kind='stable')
    active_sorted = flat_active[order]
    ids_sorted = np.zeros(flat_blocks.size, dtype=int)
    ids_sorted[active_sorted] = np.arange(1, int(active_sorted.sum()) + 1)
    elemIds = np.empty(flat_blocks.size, dtype=int)
    elemIds[order] = ids_sorted
    elemIds = elemIds.reshape(nz, ny, nx)

    # Detect fault faces while elemNodes is still 4D and elemIds is in (k,j,i)
    # layout. Recorded here, appended as paired sidesets after addSideSets runs.
    if getattr(args, 'fault_sidesets', False):
        fault_data = _detectFaultFaces(elemNodes, elemIds, active_elements)
    else:
        fault_data = None

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

    # Apply any axis flips and then strip inactive elements from every prop in
    # a single pass. The active mask and the flip decisions are constant across
    # props, so they're computed once outside the loop.
    active_mask = active_elements.flatten() > 0
    needs_flip = flip_x or flip_y
    for prop in eclipse.elemProps:
        arr = eclipse.elemProps[prop]
        if needs_flip:
            arr = arr.reshape(nz, ny, nx)
            if flip_x:
                arr = np.flip(arr, 2)
            if flip_y:
                arr = np.flip(arr, 1)
            arr = arr.flatten()
        eclipse.elemProps[prop] = arr[active_mask]

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

        # Append fault sidesets if requested. Each fault face produces two
        # sideset entries: one for the "primary" cell's face, one for the
        # "secondary" cell's face. flip_z swaps the kk_lo/kk_hi side numbers
        # (5 <-> 6) so k-direction fault entries need the same correction.
        if fault_data is not None:
            p_elems, p_sides, s_elems, s_sides = fault_data
            if args.flip_z:
                p_sides = [{5: 6, 6: 5}.get(s, s) for s in p_sides]
                s_sides = [{5: 6, 6: 5}.get(s, s) for s in s_sides]
            model.sideSets.extend([np.asarray(p_elems, dtype=int),
                                   np.asarray(s_elems, dtype=int)])
            model.sideSetSides.extend([p_sides, s_sides])
            model.sideSetNames.extend(['fault_primary', 'fault_secondary'])
            model.numSideSets = len(model.sideSets)

    # Add nodesets if required
    if args.omit_nodesets:
        model.numNodeSets = 0
    else:
        addNodeSets(model)

        # And flip the top and bottom ids if mesh is flipped
        if args.flip_z:
            model.nodeSetNames[0], model.nodeSetNames[5] = model.nodeSetNames[5], model.nodeSetNames[0]

    return model

# Corner-index permutation between the zcorn (kk, jj, ii) layout (flat index
# kk*4 + jj*2 + ii) and the eight-corner element ordering used downstream:
#   element corner 0 -> (kk=0, jj=0, ii=0) flat 0
#   element corner 1 -> (kk=0, jj=0, ii=1) flat 1
#   element corner 2 -> (kk=0, jj=1, ii=1) flat 3
#   element corner 3 -> (kk=0, jj=1, ii=0) flat 2
#   element corner 4 -> (kk=1, jj=0, ii=0) flat 4
#   element corner 5 -> (kk=1, jj=0, ii=1) flat 5
#   element corner 6 -> (kk=1, jj=1, ii=1) flat 7
#   element corner 7 -> (kk=1, jj=1, ii=0) flat 6
_CORNER_TO_KJI = [0, 1, 3, 2, 4, 5, 7, 6]

def elemCornerCoords(corner_coords):
    ''' Returns coordinates for all eight corners of each element. Input is
    shape (2*nz, 2*ny, 2*nx); output is shape (nz*ny*nx, 8) ordered in the
    eight-corner element layout. '''
    dnz, dny, dnx = corner_coords.shape
    nz, ny, nx = dnz // 2, dny // 2, dnx // 2
    # (2nz, 2ny, 2nx) -> (nz, 2, ny, 2, nx, 2) -> (nz, ny, nx, 2_kk, 2_jj, 2_ii)
    c = (corner_coords.reshape(nz, 2, ny, 2, nx, 2)
                      .transpose(0, 2, 4, 1, 3, 5)
                      .reshape(nz * ny * nx, 8))
    return c[:, _CORNER_TO_KJI]

def coordToCorn(coord, nz):
    ''' Transform coord data (x, y) coordinates to (x, y) corners for each node '''

    # Extract x and y coordinates from coord data
    xdata = np.asarray(coord[:,:,0])
    ydata = np.asarray(coord[:,:,1])

    # Repeat all internal coordinates to double the size of the arrays
    xcorn = np.repeat(np.repeat(xdata, 2, axis=0), 2, axis=1)[1:-1,1:-1]
    ycorn = np.repeat(np.repeat(ydata, 2, axis=0), 2, axis=1)[1:-1,1:-1]

    # Pillars do not vary with k, so the (2*ny, 2*nx) layer is the same for
    # every k-slice. np.broadcast_to returns a zero-copy read-only view of
    # shape (2*nz, 2*ny, 2*nx); the downstream reshape inside
    # elemCornerCoords forces a single contiguous copy at use time, rather
    # than allocating the full layered array up-front.
    xcorn = np.broadcast_to(xcorn, (2 * nz,) + xcorn.shape)
    ycorn = np.broadcast_to(ycorn, (2 * nz,) + ycorn.shape)

    return xcorn, ycorn

def elemCornToCoord(elemcorns, elemNodes):
    ''' Transform coordinate data for each element corner to a unique node ordered
    list of coordinates '''

    nodes, idx = np.unique(elemNodes, return_index=True)
    coords = elemcorns.flatten()[idx][np.nonzero(elemNodes.flatten()[idx])]

    return coords

def distortedElem(elemcornx, elemcorny, elemcornz, tol):
    ''' Returns a boolean array (numelems,) that is True for elements where any
    two corners are coincident within tol. Distorted/pinched-out elements have
    two or more corners at the same (x, y, z) location. '''
    from itertools import combinations
    corners = np.stack([elemcornx, elemcorny, elemcornz], axis=2)  # (numelems, 8, 3)
    distorted = np.zeros(corners.shape[0], dtype=bool)
    for a, b in combinations(range(8), 2):
        dist = np.linalg.norm(corners[:, a, :] - corners[:, b, :], axis=1)
        distorted |= dist < tol
    return distorted



# Pillar (j, i) offsets per element corner — see _CORNER_TO_KJI for the corner
# layout convention. Each corner sits on the pillar at (j + dj, i + di) of its
# parent cell.
_CORNER_PILLAR_DJ = np.array([0, 0, 1, 1, 0, 0, 1, 1])
_CORNER_PILLAR_DI = np.array([0, 1, 1, 0, 0, 1, 1, 0])


def numberNodesInElems(elemcornz, active_elements):
    ''' Number all unique nodes in the grid, fault-aware.

    Two corners are the same node iff they share a pillar and have equal z
    within tolerance. Implemented as a single lexsort on (pillar_id, z): every
    contiguous run in the sorted array (where pillars match and z gaps stay
    below `np.isclose`'s combined tolerance) is one node. Nodes are numbered
    by the smallest (k, j, i, corner) flat index at which an active cell first
    touches them, which matches the order the original loop assigned IDs.
    Inactive corners stay zero so the downstream filter drops their cells.
    '''
    nz, ny, nx = active_elements.shape
    n_corners = nz * ny * nx * 8
    if n_corners == 0:
        return np.zeros((nz, ny, nx, 8), dtype=int)

    # Per-corner pillar IDs of shape (ny, nx, 8); independent of k, broadcast
    # across k. pillar_id = (j + dj_c) * (nx+1) + (i + di_c).
    j_grid = np.arange(ny)[:, None, None]   # (ny, 1, 1)
    i_grid = np.arange(nx)[None, :, None]   # (1, nx, 1)
    pillar_per_layer = (j_grid + _CORNER_PILLAR_DJ) * (nx + 1) + (i_grid + _CORNER_PILLAR_DI)
    pillar_id = np.broadcast_to(pillar_per_layer, (nz, ny, nx, 8))

    # Flatten (pillar, z, active) into per-corner arrays of length 8*N.
    all_pillars = pillar_id.reshape(n_corners)
    all_z = elemcornz.reshape(n_corners)
    all_active = np.repeat(active_elements.astype(bool).flatten(), 8)

    # Sort primarily by pillar, secondarily by z (ascending).
    sort_key = np.lexsort((all_z, all_pillars))
    sp = all_pillars[sort_key]
    sz = all_z[sort_key]

    # Mark group boundaries: pillar changes, or z gap exceeds np.isclose's
    # combined tolerance (atol + rtol * max(|a|, |b|)). Sorted-ascending z
    # means gap = sz[1:] - sz[:-1] is non-negative.
    atol, rtol = 1e-8, 1e-5
    new_grp = np.empty(n_corners, dtype=bool)
    new_grp[0] = True
    if n_corners > 1:
        gap = sz[1:] - sz[:-1]
        tol_per_pair = atol + rtol * np.maximum(np.abs(sz[1:]), np.abs(sz[:-1]))
        new_grp[1:] = (sp[1:] != sp[:-1]) | (gap > tol_per_pair)
    grp_sorted = np.cumsum(new_grp) - 1
    num_groups = int(grp_sorted[-1]) + 1

    # Scatter group IDs back to original (k, j, i, c) order.
    group_id = np.empty(n_corners, dtype=np.int64)
    group_id[sort_key] = grp_sorted

    # For each group, smallest active-corner flat index (sentinel = n_corners
    # if no active member). Groups without an active member contribute no node.
    sentinel = n_corners
    first_active = np.full(num_groups, sentinel, dtype=np.int64)
    active_flat_idx = np.nonzero(all_active)[0]
    np.minimum.at(first_active, group_id[active_flat_idx], active_flat_idx)
    active_group_mask = first_active < sentinel

    # Number active groups in ascending first-active-index order — same numbering
    # the original loop produced when walking (k, j, i, corner) and assigning a
    # fresh ID at each new node it created.
    active_groups = np.nonzero(active_group_mask)[0]
    order = active_groups[np.argsort(first_active[active_groups])]
    new_id = np.zeros(num_groups, dtype=np.int64)
    new_id[order] = np.arange(1, len(order) + 1)

    # Build elemNodes; zero inactive corners so the downstream
    # ~np.any(elemNodes == 0, axis=1) filter drops inactive cells cleanly.
    elemNodes_flat = new_id[group_id] * all_active.astype(np.int64)
    return elemNodes_flat.reshape(nz, ny, nx, 8).astype(int)


def _detectFaultFaces(elemNodes, elemIds, active_elements):
    ''' Scan all internal faces of the grid and identify fault faces — those
    where two i, j, or k-adjacent cells fail to share their 4 face-corner
    node IDs (i.e. numberNodesInElems gave them different nodes because the
    z values diverged at the shared pillar).

    Returns four equal-length lists describing the paired sidesets:
      primary_elems[n], primary_sides[n]   — left/back/lower cell's face
      secondary_elems[n], secondary_sides[n] — right/front/upper cell's face

    Side numbers follow the standard Exodus II HEX8 convention used elsewhere
    in this file: 1=jj_lo, 2=ii_hi, 3=jj_hi, 4=ii_lo, 5=kk_lo, 6=kk_hi. They
    are recorded in the natural pre-flip-z element node order; the caller is
    responsible for swapping 5 <-> 6 for k-direction entries if flip_z is on.
    '''
    nz, ny, nx, _ = elemNodes.shape
    primary_elems, primary_sides = [], []
    secondary_elems, secondary_sides = [], []

    def _record(left_ids, right_ids, left_side, right_side):
        valid = (left_ids > 0) & (right_ids > 0)
        n_face = int(valid.sum())
        if n_face == 0:
            return
        primary_elems.extend(left_ids[valid].tolist())
        primary_sides.extend([left_side] * n_face)
        secondary_elems.extend(right_ids[valid].tolist())
        secondary_sides.extend([right_side] * n_face)

    active_bool = active_elements.astype(bool)

    # I-direction: cell (k, j, i) right face <-> cell (k, j, i+1) left face.
    # Shared corner pairs (left -> right): 1->0, 2->3, 5->4, 6->7.
    if nx > 1:
        left = elemNodes[:, :, :-1, :]
        right = elemNodes[:, :, 1:, :]
        both = active_bool[:, :, :-1] & active_bool[:, :, 1:]
        mismatch = (
            (left[..., 1] != right[..., 0]) |
            (left[..., 2] != right[..., 3]) |
            (left[..., 5] != right[..., 4]) |
            (left[..., 6] != right[..., 7])
        ) & both
        k_idx, j_idx, i_idx = np.where(mismatch)
        _record(elemIds[k_idx, j_idx, i_idx],
                elemIds[k_idx, j_idx, i_idx + 1],
                2, 4)

    # J-direction: cell (k, j, i) back face <-> cell (k, j+1, i) front face.
    # Shared corner pairs (back -> front): 3->0, 2->1, 7->4, 6->5.
    if ny > 1:
        back = elemNodes[:, :-1, :, :]
        front = elemNodes[:, 1:, :, :]
        both = active_bool[:, :-1, :] & active_bool[:, 1:, :]
        mismatch = (
            (back[..., 3] != front[..., 0]) |
            (back[..., 2] != front[..., 1]) |
            (back[..., 7] != front[..., 4]) |
            (back[..., 6] != front[..., 5])
        ) & both
        k_idx, j_idx, i_idx = np.where(mismatch)
        _record(elemIds[k_idx, j_idx, i_idx],
                elemIds[k_idx, j_idx + 1, i_idx],
                3, 1)

    # K-direction: cell (k, j, i) kk_hi face <-> cell (k+1, j, i) kk_lo face.
    # Shared corner pairs (lower cell -> upper cell): 4->0, 5->1, 6->2, 7->3.
    if nz > 1:
        lower = elemNodes[:-1, :, :, :]
        upper = elemNodes[1:, :, :, :]
        both = active_bool[:-1, :, :] & active_bool[1:, :, :]
        mismatch = (
            (lower[..., 4] != upper[..., 0]) |
            (lower[..., 5] != upper[..., 1]) |
            (lower[..., 6] != upper[..., 2]) |
            (lower[..., 7] != upper[..., 3])
        ) & both
        k_idx, j_idx, i_idx = np.where(mismatch)
        _record(elemIds[k_idx, j_idx, i_idx],
                elemIds[k_idx + 1, j_idx, i_idx],
                6, 5)

    return primary_elems, primary_sides, secondary_elems, secondary_sides


def _resolve_extract_range(rng, n, range_letter):
    ''' Validate a 1-based inclusive extract range against the file's axis
    size and return the 0-based half-open [lo, hi) pair to slice with. None
    means "keep the full axis". `range_letter` is the lowercase i/j/k that
    appears in the CLI flag and the SPECGRID NX/NY/NZ symbol. '''
    if rng is None:
        return 0, n
    axis = {'i': 'x', 'j': 'y', 'k': 'z'}[range_letter]
    specgrid_dim = {'i': 'NX', 'j': 'NY', 'k': 'NZ'}[range_letter]
    lo_1, hi_1 = rng
    if lo_1 > hi_1:
        print("--extract-{} requires LO <= HI, got {} > {}".format(
            range_letter, lo_1, hi_1))
        exit()
    if lo_1 < 1 or hi_1 > n:
        print("--extract-{} range {}..{} is out of bounds for the {}-axis ({}={} in SPECGRID)".format(
            range_letter, lo_1, hi_1, axis, specgrid_dim, n))
        exit()
    return lo_1 - 1, hi_1


def extractSubgrid(coord, zcorn, elemProps, nx, ny, nz,
                   i_lo, i_hi, j_lo, j_hi, k_lo, k_hi):
    ''' Slice the grid to the given (i, j, k) ranges. Inputs are in file order
    (the slice runs before any flip / translate / mapaxes); ranges are 0-based
    half-open [lo, hi).

    Inputs:
        coord     : (ny+1, nx+1, 6)        pillar top/bottom (x, y, z)
        zcorn     : (2*nz, 2*ny, 2*nx)     per-cell corner z values
        elemProps : dict[name -> flat ndarray of length nx*ny*nz]

    Returns (coord, zcorn, elemProps, new_nx, new_ny, new_nz) for the subset.
    '''
    # Pillars in (j, i): keep one extra pillar past the high end to bound the
    # last cell. .copy() decouples from the original so downstream writes (e.g.
    # the translate block) don't accidentally mutate it.
    coord = coord[j_lo:j_hi+1, i_lo:i_hi+1, :].copy()
    zcorn = zcorn[2*k_lo:2*k_hi, 2*j_lo:2*j_hi, 2*i_lo:2*i_hi].copy()

    new_elemProps = {}
    for name, vals in elemProps.items():
        p = np.asarray(vals).reshape(nz, ny, nx)[k_lo:k_hi, j_lo:j_hi, i_lo:i_hi]
        new_elemProps[name] = p.flatten()

    return coord, zcorn, new_elemProps, i_hi - i_lo, j_hi - j_lo, k_hi - k_lo


def refineLaterally(coord, zcorn, elemProps, nx, ny, nz, rx, ry):
    ''' Refine the grid laterally by integer factors (rx, ry) without refining
    vertically. Pillars (and their endpoint x, y, z stored in coord) are linearly
    interpolated. Per-cell top and bottom faces in zcorn are bilinearly
    interpolated within each parent cell, which preserves faults (z jumps
    between adjacent cells along a shared pillar). Element properties are tiled
    so each child inherits its parent's value.

    Inputs:
        coord     : ndarray (ny+1, nx+1, 6)     pillar top/bottom (x, y, z)
        zcorn     : ndarray (2*nz, 2*ny, 2*nx)  per-cell corner z values
        elemProps : dict[name -> flat ndarray of length nx*ny*nz]
        nx, ny, nz: int grid sizes
        rx, ry    : int positive refinement factors

    Returns:
        (coord, zcorn, elemProps, nx*rx, ny*ry) with refined shapes.
    '''
    if rx == 1 and ry == 1:
        return coord, zcorn, elemProps, nx, ny

    # COORD: linear interpolation between pillars along j then i.
    coord = _refine_axis(coord, ry, axis=0)
    coord = _refine_axis(coord, rx, axis=1)

    # ZCORN: bilinear within each parent cell. Per-cell corner arrays each of
    # shape (nz, ny, nx); naming c<u><v><k> with u, v in {0, 1} for the (i, j)
    # corner and k in {0, 1} for top/bottom.
    c000 = zcorn[0::2, 0::2, 0::2]
    c100 = zcorn[0::2, 0::2, 1::2]
    c010 = zcorn[0::2, 1::2, 0::2]
    c110 = zcorn[0::2, 1::2, 1::2]
    c001 = zcorn[1::2, 0::2, 0::2]
    c101 = zcorn[1::2, 0::2, 1::2]
    c011 = zcorn[1::2, 1::2, 0::2]
    c111 = zcorn[1::2, 1::2, 1::2]

    # Parametric (u, v) at every sub-cell corner in zcorn order. Interior values
    # appear twice because adjacent sub-cells own their own copy of a shared
    # corner. For rx = 3: [0, 1/3, 1/3, 2/3, 2/3, 1].
    u_seq = np.repeat(np.arange(rx + 1) / rx, 2)[1:-1]
    v_seq = np.repeat(np.arange(ry + 1) / ry, 2)[1:-1]
    u = u_seq.reshape(1, 1, 1, 1, 2 * rx)
    v = v_seq.reshape(1, 1, 1, 2 * ry, 1)

    def bilinear(z00, z10, z01, z11):
        z00 = z00[..., None, None]
        z10 = z10[..., None, None]
        z01 = z01[..., None, None]
        z11 = z11[..., None, None]
        return ((1 - u) * (1 - v) * z00
                +      u  * (1 - v) * z10
                + (1 - u) *      v  * z01
                +      u  *      v  * z11)

    z_top = bilinear(c000, c100, c010, c110)
    z_bot = bilinear(c001, c101, c011, c111)

    # Collapse (ny, 2*ry) -> 2*ry*ny and (nx, 2*rx) -> 2*rx*nx by transposing
    # so the parent axis sits adjacent to its sub-corner axis, then reshaping.
    def collapse(z):
        return z.transpose(0, 1, 3, 2, 4).reshape(nz, 2 * ry * ny, 2 * rx * nx)
    z_top = collapse(z_top)
    z_bot = collapse(z_bot)

    zcorn_new = np.empty((2 * nz, 2 * ry * ny, 2 * rx * nx), dtype=zcorn.dtype)
    zcorn_new[0::2] = z_top
    zcorn_new[1::2] = z_bot

    new_elemProps = {}
    for name, vals in elemProps.items():
        p = np.asarray(vals).reshape(nz, ny, nx)
        p = np.repeat(np.repeat(p, ry, axis=1), rx, axis=2)
        new_elemProps[name] = p.flatten()

    return coord, zcorn_new, new_elemProps, nx * rx, ny * ry


def _refine_axis(a, r, axis):
    ''' Linearly interpolate `a` along `axis` so that n+1 nodes become r*n+1. '''
    if r == 1:
        return a
    n = a.shape[axis] - 1
    left  = np.take(a, np.arange(0, n),     axis=axis)
    right = np.take(a, np.arange(1, n + 1), axis=axis)
    left  = np.expand_dims(left,  axis + 1)
    right = np.expand_dims(right, axis + 1)
    s_shape = [1] * left.ndim
    s_shape[axis + 1] = r
    s = (np.arange(r) / r).reshape(s_shape)
    blended = (1 - s) * left + s * right
    new_shape = list(blended.shape)
    new_shape[axis] = n * r
    del new_shape[axis + 1]
    interior = blended.reshape(new_shape)
    last = np.take(a, [n], axis=axis)
    return np.concatenate([interior, last], axis=axis)
