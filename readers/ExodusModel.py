# Class for Exodus model object

class ExodusModel(object):
    '''Class containing all components of an Exodus II mesh'''

    def __init__(self, dim = 3):
        self._dim = dim
        self._xcoords = []
        self._ycoords = []
        self._zcoords = []
        self._nodeIds = None
        self._elemIds = None
        self._elemNodes = None
        self._elemVars = None
        self._nodeVars = None
        self._blockIds = None

    # Dimension
    @property
    def dim(self):
        return self._dim

    @dim.setter
    def dim(self, dim):
        self._dim = dim

    # Nodal coordinates in x, y and z directions
    @property
    def xcoords(self):
        return self._xcoords

    @xcoords.setter
    def xcoords(self, coords):
        self._xcoords = coords

    @property
    def ycoords(self):
        return self._ycoords

    @ycoords.setter
    def ycoords(self, coords):
        self._ycoords = coords

    @property
    def zcoords(self):
        return self._zcoords

    @zcoords.setter
    def zcoords(self, coords):
        self._zcoords = coords

    # Node IDs
    @property
    def nodeIds(self):
        return self._nodeIds

    @nodeIds.setter
    def nodeIds(self, ids):
        self._nodeIds = ids

    # Element IDs
    @property
    def elemIds(self):
        return self._elemIds

    @elemIds.setter
    def elemIds(self, ids):
        self._elemIds = ids

    # Node IDs for each element (the element connectivity)
    @property
    def elemNodes(self):
        return self._elemNodes

    @elemNodes.setter
    def elemNodes(self, ids):
        self._elemNodes = ids

    # Elemental variables
    @property
    def elemVars(self):
        return self._elemVars

    @elemVars.setter
    def elemVars(self, vars):
        self._elemVars = vars

    # Nodal variables
    @property
    def nodeVars(self):
        return self._nodeVars

    @nodeVars.setter
    def nodeVars(self, vars):
        self._nodeVars = vars

    # Block IDs
    @property
    def blockIds(self):
        return self._blockIds

    @blockIds.setter
    def blockIds(self, ids):
        self._blockIds = ids
