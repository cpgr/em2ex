# Function to assign node numbers while avoiding duplicates

def addNode(array, i, j, k, count):
    '''Utility to generate unique node numbers using right-hand rule'''
    if array[k,j,i] == 0:
        # Node hasn't been numbered
        array[k,j,i] = count
        count += 1
        return count
    else:
        # Node has already been numbered
        return count
