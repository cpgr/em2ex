# Functions to read Eclipse grdecl files and parse the input

import numpy as np

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

def readBlockHDF5(f, d, chunksize=1e6):
    '''Reads block of data and saves it to a HDF5 dataset in chunks'''
    block = []
    pos = 0
    end = False
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
            end = True
        # Save to HDF5 dataset if number of individual data elements is greater than chunksize
        if len(block) > int(chunksize) or end == True:
            block = map(float, block)
            d[pos:pos+len(block)] = np.asarray(block)
            pos += len(block)
            block = []
        # End read if line ends with /
        if end == True:
            break
    return

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

def readKeywordHDF5(f, keyword, d, chunksize=1e6):
    '''Read keyword data from grdecl file and save it to a HDF5 dataset in chunks'''
    for line in f:
        # Skip comments and blank lines
        if line.startswith('--') or not line.strip():
            continue

        elif line.startswith(keyword):
            readBlockHDF5(f, d, chunksize)

        else:
            # Skip all unknown sections
            continue

    return

def parseEclipse(f):
    '''Parse the ECLIPSE file and return node coordinates and material properties'''

    # Keywords that may be read in the Eclipse file
    ECLIPSE_KEYWORDS =  ['ACTNUM', 'SATNUM', 'PORO', 'PERMX', 'PERMY', 'PERMZ']

    # Open the .grdecl file for reading
    file = open(f)

    # Dict for storing reservoir properties
    props = {};

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
            props[prop] = proplistname

        else:
            # Skip all unkown sections
            continue

    # Close the file after parsing
    file.close()

    # The number of elements in the x, y and z directions are specified in the SPECGRID data
    nx = int(specgridlist[0])
    ny = int(specgridlist[1])
    nz = int(specgridlist[2])

    # Check the number of COORD entries parsed is correct (6 points per entry)
    if (nx+1)*(ny+1)*6 != len(coordlist):
        print("The number of COORD entries read is not correct")
        exit()

    # Check the number of ZCORN entries parsed is correct
    if (2 * nx)*(2 * ny) *(2 * nz) != len(zcornlist):
        print("The number of ZCORN entries read is not correct")
        exit()

    # Check all of the properties that have been parsed
    for prop in props:
        if len(props[prop]) != nx*ny*nz:
            print "The number of", prop, "entries read is not correct"
            exit()

    # Notify user that parsing has finished
    print("Finished parsing Eclipse file")

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

    return nx, ny, nz, xdata, ydata, zdata, props
