# Function to assign node numbers while avoiding duplicates

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

def addSideSets(elemIds):
    ''' Utility to determine elements in sidesets from array of element ids '''

    # Sidesets for the boundaries of the model (note: assumes 3D model)
    sideSets = []
    sideSets.append(elemIds[0,:,:].flatten().tolist())
    sideSets.append(elemIds[:,0,:].flatten().tolist())
    sideSets.append(elemIds[:,:,0].flatten().tolist())
    sideSets.append(elemIds[:,:,-1].flatten().tolist())
    sideSets.append(elemIds[:,-1,:].flatten().tolist())
    sideSets.append(elemIds[-1:,:].flatten().tolist())

    return sideSets

def addSideSetSides(sideSets):
    ''' Utility to add sideset IDs from list of sidesets '''

    # Sideset side numbers (note: assumes 3D model)
    sideSetSides = []
    sideSetSides.append([5] * len(sideSets[0]))
    sideSetSides.append([1] * len(sideSets[1]))
    sideSetSides.append([4] * len(sideSets[2]))
    sideSetSides.append([2] * len(sideSets[3]))
    sideSetSides.append([3] * len(sideSets[4]))
    sideSetSides.append([6] * len(sideSets[5]))

    return sideSetSides

def addNodeSets(nodeIds):
    ''' Utility to determine nodes in nodesets from array of node ids '''

    # Nodesets for the boundaries of the model (note: assumes 3D model)
    nodeSets = []
    nodeSets.append(nodeIds[0,:,:].flatten().tolist())
    nodeSets.append(nodeIds[:,0,:].flatten().tolist())
    nodeSets.append(nodeIds[:,:,0].flatten().tolist())
    nodeSets.append(nodeIds[:,:,-1].flatten().tolist())
    nodeSets.append(nodeIds[:,-1,:].flatten().tolist())
    nodeSets.append(nodeIds[-1,:,:].flatten().tolist())

    return nodeSets
