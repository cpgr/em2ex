import numpy as np
from exodus_model.ExodusModel import ExodusModel

def addNode(array, i, j, k, count):
    ''' Utility to generate unique node numbers using right-hand rule '''
    if array[k,j,i] == 0:
        # Node hasn't been numbered
        array[k,j,i] = count
        count += 1
        return count
    else:
        # Node has already been numbered
        return count

def addSideSets(model):
    ''' Utility to determine elements in sidesets from array of element ids '''

    # Sidesets for the boundaries of the model (note: assumes 3D model)
    sideSets = []

    # Copy the elemIds to avoid changing elemIds (arrays arguments are mutable)
    ids = np.copy(model.elemIds)

    # XY planes
    sideSets.append(nonZeroValues(ids))
    sideSets.append(nonZeroValues(np.flip(ids, axis=0)))

    # YZ planes
    ids = np.copy(model.elemIds)
    ids = np.rot90(ids, axes=(0,1))
    sideSets.insert(1, nonZeroValues(ids))
    sideSets.insert(1, nonZeroValues(np.flip(ids, axis=0)))

    # XZ planes
    ids = np.copy(model.elemIds)
    ids = np.rot90(ids, axes=(0,2))
    sideSets.insert(2, nonZeroValues(ids))
    sideSets.insert(2, nonZeroValues(np.flip(ids, axis=0)))

    # Sideset side numbers (note: assumes 3D model)
    sideSetSides = []
    sideSetSides.append([5] * len(sideSets[0]))
    sideSetSides.append([1] * len(sideSets[1]))
    sideSetSides.append([4] * len(sideSets[2]))
    sideSetSides.append([2] * len(sideSets[3]))
    sideSetSides.append([3] * len(sideSets[4]))
    sideSetSides.append([6] * len(sideSets[5]))

    # Add sidesets to model
    # Sideset names
    model.sideSetNames = ['bottom', 'front', 'left', 'right', 'back', 'top']

    # Sidesets for the boundaries of the model
    model.sideSets = sideSets

    # Sideset side numbers
    model.sideSetSides = sideSetSides

    # Number of sidesets
    model.numSideSets = len(sideSets)

    return

def addNodeSets(model):
    ''' Utility to determine nodes in nodesets from array of node ids '''

    # Nodesets for the boundaries of the model (note: assumes 3D model)
    nodeSets = []

    # Copy the elemIds to avoid changing elemIds (arrays arguments are mutable)
    ids = np.copy(model.nodeIds)

    # XY planes
    nodeSets.append(nonZeroValues(ids))
    nodeSets.append(nonZeroValues(np.flip(ids, axis=0)))

    # YZ planes
    ids = np.copy(model.nodeIds)
    ids = np.rot90(ids, axes=(0,1))
    nodeSets.insert(1, nonZeroValues(ids))
    nodeSets.insert(1, nonZeroValues(np.flip(ids, axis=0)))

    # XZ planes
    ids = np.copy(model.nodeIds)
    ids = np.rot90(ids, axes=(0,2))
    nodeSets.insert(2, nonZeroValues(ids))
    nodeSets.insert(2, nonZeroValues(np.flip(ids, axis=0)))

    # Add nodesets to model
    model.nodeSetNames = ['bottom', 'front', 'left', 'right', 'back', 'top']

    # Nodesets for the boundaries of the model (note: assumes 3D model)
    model.nodeSets = nodeSets

    # Number of nodesets
    model.numNodeSets = len(nodeSets)

    return

# Per-corner edge index table for HEX8 Jacobian computation. Each entry gives
# the three edge vector specifications (P[a] - P[b]) for the +xi, +eta, +zeta
# directions at that corner. The Jacobian at corner c is the scalar triple
# product of those three edge vectors; for a well-formed HEX8 it is positive
# at every corner.
_HEX8_JAC_EDGES = [
    ((1, 0), (3, 0), (4, 0)),  # corner 0
    ((1, 0), (2, 1), (5, 1)),  # corner 1
    ((2, 3), (2, 1), (6, 2)),  # corner 2
    ((2, 3), (3, 0), (7, 3)),  # corner 3
    ((5, 4), (7, 4), (4, 0)),  # corner 4
    ((5, 4), (6, 5), (5, 1)),  # corner 5
    ((6, 7), (6, 5), (6, 2)),  # corner 6
    ((6, 7), (7, 4), (7, 3)),  # corner 7
]


# Edge node pairs for a HEX8 element, in the standard Exodus corner ordering
# (nodes 0-3 on the lower face, 4-7 on the upper face). The last four are the
# k-direction edges, reported separately as the cell thickness.
_HEX8_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),   # lower face
    (4, 5), (5, 6), (6, 7), (7, 4),   # upper face
    (0, 4), (1, 5), (2, 6), (3, 7),   # vertical (k-direction)
]
_HEX8_VERTICAL_EDGES = _HEX8_EDGES[8:]

# Opposite-face node groups defining the three principal axes of a HEX8, used
# for the skew metric. Each axis runs from the centroid of the low face to the
# centroid of the high face in one parametric direction; skew is the largest
# absolute cosine between any pair of (normalised) axes, so 0 is a perfectly
# orthogonal cell and 1 is fully collapsed.
_HEX8_PRINCIPAL_AXES = [
    ((1, 2, 6, 5), (0, 3, 7, 4)),   # xi
    ((2, 3, 7, 6), (0, 1, 5, 4)),   # eta
    ((4, 5, 6, 7), (0, 1, 2, 3)),   # zeta
]

# Parametric corner coordinates of the HEX8 shape functions, in element order.
_HEX8_XI   = np.array([-1., 1., 1., -1., -1., 1., 1., -1.])
_HEX8_ETA  = np.array([-1., -1., 1., 1., -1., -1., 1., 1.])
_HEX8_ZETA = np.array([-1., -1., -1., -1., 1., 1., 1., 1.])


def _elementCornerPoints(model):
    ''' Return the (num_elems, 8, 3) array of corner coordinates for every
    element, gathered from the model's node coordinates via elemNodes. '''
    node_idx = model.elemNodes - 1   # 0-based node indices
    x = np.asarray(model.xcoords)[node_idx]   # (num_elems, 8)
    y = np.asarray(model.ycoords)[node_idx]
    z = np.asarray(model.zcoords)[node_idx]
    return np.stack([x, y, z], axis=-1)


def _exodusElementIds(model):
    ''' Map each elemNodes row to its 1-based Exodus element ID. elemIds[k, j, i]
    holds the ID (0 for inactive); the non-zero values in (k, j, i) flat order
    align with elemNodes' row ordering. '''
    if model.elemIds is not None:
        exodus_ids = np.asarray(model.elemIds).flatten()
        return exodus_ids[exodus_ids > 0]
    return np.arange(1, model.numElems + 1)


def hex8Volumes(P):
    ''' Exact volume of each trilinear HEX8 element.

    The Jacobian determinant of a trilinear map is at most quadratic in each
    parametric coordinate, so 2x2x2 Gauss quadrature (all weights 1) integrates
    it exactly. Input is (num_elems, 8, 3); output is (num_elems,). Volumes are
    signed — inverted elements return negative values, matching the sign
    convention of the Jacobian check.
    '''
    g = 1.0 / np.sqrt(3.0)
    volumes = np.zeros(P.shape[0])
    for s1 in (-g, g):
        for s2 in (-g, g):
            for s3 in (-g, g):
                dN = np.empty((8, 3))
                dN[:, 0] = 0.125 * _HEX8_XI   * (1 + _HEX8_ETA * s2) * (1 + _HEX8_ZETA * s3)
                dN[:, 1] = 0.125 * _HEX8_ETA  * (1 + _HEX8_XI  * s1) * (1 + _HEX8_ZETA * s3)
                dN[:, 2] = 0.125 * _HEX8_ZETA * (1 + _HEX8_XI  * s1) * (1 + _HEX8_ETA  * s2)
                volumes += np.linalg.det(np.einsum('nac,ad->ncd', P, dN))
    return volumes


def hex8AspectRatios(P):
    ''' Ratio of longest to shortest edge for each HEX8 element (the edge
    ratio). 1.0 is a cube; large values mean a stretched cell, which for a
    corner point reservoir grid almost always means thin in z relative to its
    lateral extent. Elements with a zero-length edge return inf. '''
    edge_lengths = _hex8EdgeLengths(P, _HEX8_EDGES)
    shortest = edge_lengths.min(axis=1)
    longest = edge_lengths.max(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(shortest > 0, longest / shortest, np.inf)


def hex8Thicknesses(P):
    ''' Mean length of the four k-direction edges of each HEX8 element. This is
    the cell thickness, and is reported alongside the aspect ratio because it
    identifies whether a poor ratio comes from thin layers (the usual cause in
    a reservoir grid) or from large lateral cells. '''
    return _hex8EdgeLengths(P, _HEX8_VERTICAL_EDGES).mean(axis=1)


def hex8Skews(P):
    ''' Skew of each HEX8 element: the largest absolute cosine of the angle
    between any pair of principal axes. 0 is perfectly orthogonal, 1 is
    collapsed. Elements with a zero-length principal axis are already
    degenerate and return 1.0. '''
    axes = np.empty((P.shape[0], 3, 3))
    for a, (high_face, low_face) in enumerate(_HEX8_PRINCIPAL_AXES):
        axes[:, a, :] = (P[:, high_face, :].sum(axis=1)
                         - P[:, low_face, :].sum(axis=1))

    norms = np.linalg.norm(axes, axis=2)                    # (num_elems, 3)
    degenerate = np.any(norms == 0, axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        unit_axes = axes / norms[:, :, None]

    skew = np.zeros(P.shape[0])
    for a, b in ((0, 1), (0, 2), (1, 2)):
        skew = np.maximum(
            skew, np.abs(np.einsum('ij,ij->i', unit_axes[:, a], unit_axes[:, b])))

    skew[degenerate] = 1.0
    return skew


def _hex8EdgeLengths(P, edges):
    ''' Lengths of the given node-pair edges for every element. Output is
    (num_elems, len(edges)). '''
    starts = [e[0] for e in edges]
    ends = [e[1] for e in edges]
    return np.linalg.norm(P[:, ends, :] - P[:, starts, :], axis=2)


# Percentiles reported for every metric in the mesh quality report.
_QUALITY_PERCENTILES = (0, 5, 25, 50, 75, 95, 100)
_QUALITY_HEADINGS = ('min', '5%', '25%', 'median', '75%', '95%', 'max')


def _formatStatRow(label, values, width=11):
    ''' Format one metric row to four significant figures. The `#.4g` format
    keeps trailing zeros so the columns line up, and falls back to an exponent
    only for values too large or small to show otherwise — which matters
    because cell volumes routinely span several orders of magnitude while
    aspect ratio and skew do not. '''
    cells = ''.join('{:>#{w}.4g}'.format(v, w=width) for v in values)
    return '  {:<16}{}'.format(label, cells)


def meshQualityReport(model, aspect_thresholds=(10.0, 50.0), skew_threshold=0.5,
                      num_examples=5):
    ''' Print a distribution summary of element shape quality for the mesh.

    Reports aspect ratio (longest edge / shortest edge), skew, cell thickness
    and cell volume as percentile spreads, followed by the count of elements
    exceeding each aspect ratio threshold and the skew threshold, and the
    location of the worst offenders.

    This is a reporting function only — it never alters the mesh and never
    exits non-zero. It is reader-agnostic, working from elemNodes and the node
    coordinates, so it applies to both Eclipse and Leapfrog models.

    Returns a dict of the computed per-element metric arrays, so callers (and
    tests) can assert on the numbers rather than parsing stdout.
    '''
    if model.elemNodes is None or not model.numElems:
        print('Mesh quality report: no elements to report on')
        return {}

    P = _elementCornerPoints(model)
    metrics = {
        'aspect ratio': hex8AspectRatios(P),
        'skew': hex8Skews(P),
        'thickness': hex8Thicknesses(P),
        'volume': hex8Volumes(P),
    }

    aspect = metrics['aspect ratio']
    skew = metrics['skew']
    num_elems = model.numElems

    # Degenerate elements (a collapsed edge, so an infinite aspect ratio) are
    # held out of the statistics below and counted on their own line. They
    # cannot be included: np.percentile interpolates linearly, so a single
    # infinity turns most of the row into NaN. Holding them out keeps the
    # percentile rows and the threshold counts describing the same population.
    finite = np.isfinite(aspect)
    num_degenerate = int(np.sum(~finite))

    print('Mesh quality report: {} elements'.format(model.numElems))
    print('  {:<16}{}'.format(
        '', ''.join('{:>11}'.format(h) for h in _QUALITY_HEADINGS)))
    if not np.any(finite):
        print('  (every element has a zero-length edge; no statistics to report)')
    else:
        for label, values in metrics.items():
            print(_formatStatRow(
                label, np.percentile(values[finite], _QUALITY_PERCENTILES)))

    def _count_line(text, count):
        print('  {:<40}{:>8}  ({:.1f}%)'.format(
            text, count, 100.0 * count / num_elems))

    print('  Elements exceeding quality thresholds:')
    for threshold in aspect_thresholds:
        _count_line('aspect ratio > {:g}'.format(threshold),
                    int(np.sum(aspect[finite] > threshold)))
    _count_line('skew > {:g}'.format(skew_threshold),
                int(np.sum(skew[finite] > skew_threshold)))

    if num_degenerate:
        _count_line('zero-length edge (excluded above)', num_degenerate)

    # Locate the worst cells by aspect ratio so the user can see whether the
    # problem is concentrated in a few layers or spread through the model.
    # Degenerate cells sort to the top, which is where they belong.
    worst_threshold = max(aspect_thresholds) if aspect_thresholds else np.inf
    if num_degenerate or np.any(aspect[finite] > worst_threshold):
        exodus_ids = _exodusElementIds(model)
        worst_rows = np.argsort(aspect)[::-1][:num_examples]
        print('  Worst elements by aspect ratio:')
        for r in worst_rows:
            eid = int(exodus_ids[r]) if r < len(exodus_ids) else r + 1
            cx, cy, cz = P[r].mean(axis=0)
            print('    element {}: aspect ratio {:.4g}, thickness {:.4g}, '
                  'centroid ({:.4g}, {:.4g}, {:.4g})'.format(
                      eid, aspect[r], metrics['thickness'][r], cx, cy, cz))

    return metrics


def checkElementJacobians(model, strict=False):
    ''' Compute the per-corner Jacobian for every HEX8 element and report any
    elements with non-positive Jacobian (degenerate or inverted).

    Prints a one-line summary. If any problem cells are found, expands the
    output with element IDs and centroid locations for the first few examples
    in each category (negative, zero). If `strict` is True, exits non-zero
    when any non-positive Jacobian is detected; otherwise returns False as a
    soft signal but continues execution.

    Returns True if all elements have positive Jacobian everywhere.
    '''
    if model.elemNodes is None or model.numElems == 0:
        return True

    P = _elementCornerPoints(model)           # (num_elems, 8, 3)

    jacobians = np.empty((P.shape[0], 8))
    for c, ((xi_a, xi_b), (eta_a, eta_b), (zeta_a, zeta_b)) in enumerate(_HEX8_JAC_EDGES):
        e_xi   = P[:, xi_a]   - P[:, xi_b]
        e_eta  = P[:, eta_a]  - P[:, eta_b]
        e_zeta = P[:, zeta_a] - P[:, zeta_b]
        jacobians[:, c] = np.einsum('ij,ij->i', e_xi, np.cross(e_eta, e_zeta))

    min_jac = jacobians.min(axis=1)
    num_neg  = int(np.sum(min_jac < 0))
    num_zero = int(np.sum(min_jac == 0))
    num_ok   = model.numElems - num_neg - num_zero

    if num_neg == 0 and num_zero == 0:
        print('Element Jacobian check: {} / {} elements OK'.format(num_ok, model.numElems))
        return True

    print('Element Jacobian check: {} negative, {} zero, {} OK (out of {})'.format(
        num_neg, num_zero, num_ok, model.numElems))

    if num_ok == 0:
        print('  All elements have non-positive Jacobians. Possible causes:')
        print('    - z-up coordinate convention: try --flip to invert the z-axis')
        print('    - Orientation-reversing coordinate system (e.g. MAPAXES handedness)')
        print('  Use --remove-distorted to remove these elements and proceed anyway.')

    exodus_ids = _exodusElementIds(model)

    for label, mask in (('negative', min_jac < 0), ('zero', min_jac == 0)):
        bad_rows = np.where(mask)[0]
        if len(bad_rows) == 0:
            continue
        print('  Examples of {}-Jacobian elements (showing up to 5 of {}):'.format(
            label, len(bad_rows)))
        for r in bad_rows[:5]:
            eid = int(exodus_ids[r]) if r < len(exodus_ids) else r + 1
            cx, cy, cz = P[r].mean(axis=0)
            print('    element {}: centroid ({:.4g}, {:.4g}, {:.4g}), min Jacobian = {:.3e}'.format(
                eid, cx, cy, cz, min_jac[r]))

    if strict:
        print('--strict-jacobians: exiting due to invalid Jacobians')
        exit(1)

    return False


def nonPositiveJacobianElems(elemcornx, elemcorny, elemcornz):
    ''' Return a boolean array (numelems,) that is True for elements whose
    minimum per-corner Jacobian is <= 0 (degenerate or inverted).

    Inputs are per-element corner coordinate arrays of shape (numelems, 8),
    ordered in the HEX8 element corner layout (matching elemCornerCoords output).
    '''
    P = np.stack([elemcornx, elemcorny, elemcornz], axis=-1)  # (N, 8, 3)
    jacobians = np.empty((P.shape[0], 8))
    for c, ((xi_a, xi_b), (eta_a, eta_b), (zeta_a, zeta_b)) in enumerate(_HEX8_JAC_EDGES):
        e_xi   = P[:, xi_a]   - P[:, xi_b]
        e_eta  = P[:, eta_a]  - P[:, eta_b]
        e_zeta = P[:, zeta_a] - P[:, zeta_b]
        jacobians[:, c] = np.einsum('ij,ij->i', e_xi, np.cross(e_eta, e_zeta))
    return jacobians.min(axis=1) <= 0


def nonZeroValues(arr):
    ''' Utility to determine first non-zero values in the top plane of an array '''

    values = []

    for i in range(0, arr.shape[1]):
        for j in range(0, arr.shape[2]):
            if arr[0, i, j] > 0:
                values.append(arr[0,i,j])
            else:
                # descend in column [:,i,j] until a non-zero value is found
                if arr[:, i, j][arr[:, i, j]>0].size > 0:
                    values.append(arr[:, i, j][arr[:, i, j]>0][0])

    # Sort and make sure the values are unique
    values = np.array(values, dtype = int)
    return np.unique(values)
