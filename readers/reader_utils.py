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

    node_idx = model.elemNodes - 1   # 0-based node indices
    x = np.asarray(model.xcoords)[node_idx]   # (num_elems, 8)
    y = np.asarray(model.ycoords)[node_idx]
    z = np.asarray(model.zcoords)[node_idx]
    P = np.stack([x, y, z], axis=-1)          # (num_elems, 8, 3)

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

    # Map elemNodes row -> Exodus element ID. elemIds[k, j, i] holds the
    # 1-based Exodus ID (0 for inactive); the non-zero values in (k, j, i)
    # flat order align with elemNodes' row ordering.
    if model.elemIds is not None:
        exodus_ids = np.asarray(model.elemIds).flatten()
        exodus_ids = exodus_ids[exodus_ids > 0]
    else:
        exodus_ids = np.arange(1, model.numElems + 1)

    for label, mask in (('negative', min_jac < 0), ('zero', min_jac == 0)):
        bad_rows = np.where(mask)[0]
        if len(bad_rows) == 0:
            continue
        print('  Examples of {}-Jacobian elements (showing up to 5 of {}):'.format(
            label, len(bad_rows)))
        for r in bad_rows[:5]:
            eid = int(exodus_ids[r]) if r < len(exodus_ids) else r + 1
            cx, cy, cz = float(x[r].mean()), float(y[r].mean()), float(z[r].mean())
            print('    element {}: centroid ({:.4g}, {:.4g}, {:.4g}), min Jacobian = {:.3e}'.format(
                eid, cx, cy, cz, min_jac[r]))

    if strict:
        print('--strict-jacobians: exiting due to invalid Jacobians')
        exit(1)

    return False


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
