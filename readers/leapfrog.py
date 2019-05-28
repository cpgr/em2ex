# Functions to read Leapfrog CSV files and parse the input

import numpy as np
import pandas as pd
import re
from ExodusModel import ExodusModel
from nodeutils import addNode

def parseLeapfrog(f):
    '''Parse the Leapfrog file and return node coordinates and material properties'''

    # The number of elements in the x, y and z directions are specified on line 6 of the Leapfrog export CSV
#filename + '.e'
    with open(f + "_cell.csv", 'r') as fid:
        content = fid.read()

    match = re.search(r'size\s*in\s*blocks:\s*(?P<size>.*?)\s*=', content)
    if match:
        block_size = [int(x) for x in match.group('size').split()]
    else:
        print "Could not locate block size in {}".format(f)
    # Close the file after parsing
    fid.close()

    nx = block_size[0]
    ny = block_size[1]
    nz = block_size[2]

##################################################################
#handle material properties

    # Dict for storing reservoir properties, full of numpy arrays
    props = {};

    # Reopen the Leapfrog file with pandas to directly build property tables
    cell_file = pd.read_csv(f + "_cell.csv", skiprows=10)

    # look for material properties in the CSV file (don't want X, Y Z locs from cell data, get from node file)
    #first get a list if the properties in the CSV file, then loop into it to put data into dictionary
    n = list(cell_file.shape)
    numprops = n[1]
    headers = cell_file.columns.values.tolist()

    for prop in range(7, numprops): #there are always 7 columns in the csv file before you get to the properties
        prop = headers[prop]
        proplistname = prop.lower() + 'list'
        proplistname = np.asarray(cell_file[prop].tolist())
        props[prop] = proplistname

##################################################################
#handle primary variables

    ##Now need to get node locations and values for primary variables
    variables = {};


    # look for vaariable valuess in the node CSV file
    node_file = pd.read_csv(f +"_node.csv", skiprows=10)
    n2 = list(node_file.shape)
    numvariables = n2[1]
    variable_headers = node_file.columns.values.tolist()


    for variable in range(7, numvariables): #there are always 7 columns before you get to the properties
        variable = variable_headers[variable]
        variablelistname = variable.lower() + 'list'
        variablelistname = np.asarray(node_file[variable].tolist())
        variables[variable] = variablelistname


##################################################################

    # Notify user that parsing has finished
    print("Finished parsing Leapfrog file")
    print "There were ", numprops - 7, " material properties found"
    print "There were ",numvariables - 7, " nodal variable values found"
    print "Mesh dimensions are nx: ",nx," ny: ", ny," nz: ", nz


    # Now build node location arrays. The x and y data are taken firectly from the pandas node table.
    xdata_list = np.asarray(node_file['X'].tolist())
    xdata = xdata_list.reshape((nz+1,ny+1,nx+1))

    ydata_list = np.asarray(node_file['Y'].tolist())
    ydata = ydata_list.reshape((nz+1,ny+1,nx+1))

    zdata_list = np.asarray(node_file['Z'].tolist())
    zdata = zdata_list.reshape((nz+1,ny+1,nx+1))

    # Loop through the elements and add the node numbers following the right-hand rule,
    # starting at 1. Also construct the element connectivity array
    nodeIds = np.zeros((nz+1, ny+1, nx+1), dtype=int)
    elemNodes = np.zeros((nz*ny*nx, 8), dtype=int)
    elemIds = np.zeros((nz, ny, nx), dtype=int)
    node_list = np.zeros((nz+1) * (ny+1) * (nx+1))

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

    print len(xcoords)
    print len(zcoords)
    n = 0
    for k in range(0,nz+1):
        for j in range(0,ny+1):
            for i in range(0,nx+1):
                # Get the node number corresponding to i,j,k
                # Note that the array position is node_id - 1
                nid = nodeIds[k,j,i]
                xcoords[nid-1] = xdata[k,j,i]
                ycoords[nid-1] = ydata[k,j,i]
                zcoords[nid-1] = zdata[k,j,i]
                node_list[n] = nid
                n += 1


    node_order = np.asarray(node_list)
    pressure = np.asarray(node_file['pressure'])  # can add .tolist() to mke these lists
    temperature = np.asarray(node_file['temperature'])
    temp = np.column_stack((node_order, pressure, temperature))

    # NUMPY BASED VERSION
    #this sorts the nodel variables to that they are in th same order of as the node IDs generated above
    sort_index = np.argsort(node_list)

    #and updates the dictionary
    variables['pressure'] = pressure[sort_index]
    variables['temperature'] = temperature[sort_index]

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
    model.elemVars = props
    model.nodeVars = variables

    # Block IDs (assume only one block ID currently)
    model.blockIds = np.zeros(elemIds.size).astype(int)

    return model
