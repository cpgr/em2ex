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
