# Class for Exodus model object

class ExodusModel(object):
    '''Class containing all components of an Exodus II mesh'''

    def __init__(self, dim = 3):
        self._dim = dim
        self._xcoords = None
        self._ycoords = None
        self._zcoords = None
        self._nodeIds = None
        self._elemIds = None
        self._elemNodes = None
        self._elemVars = None
        self._nodeVars = None
        self._blockIds = None
        self._sideSetNames = None
        self._sideSets = None
        self._sideSetSides = None
        self._nodeSetNames = None
        self._nodeSets = None

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

    # Sideset names
    @property
    def sideSetNames(self):
        return self._sideSetNames

    @sideSetNames.setter
    def sideSetNames(self, names):
        self._sideSetNames = names

    # Sidesets (list of elements in sideset)
    @property
    def sideSets(self):
        return self._sideSets

    @sideSets.setter
    def sideSets(self, sidesets):
        self._sideSets = sidesets

    # Sideset sides (number associated with each sideset)
    @property
    def sideSetSides(self):
        return self._sideSetSides

    @sideSetSides.setter
    def sideSetSides(self, sidesetsides):
        self._sideSetSides = sidesetsides

    # Nodeset names
    @property
    def nodeSetNames(self):
        return self._nodeSetNames

    @nodeSetNames.setter
    def nodeSetNames(self, names):
        self._nodeSetNames = names

    # Nodesets
    @property
    def nodeSets(self):
        return self._nodeSets

    @nodeSets.setter
    def nodeSets(self, nodesets):
        self._nodeSets = nodesets
