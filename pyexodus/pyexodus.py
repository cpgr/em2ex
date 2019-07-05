from netCDF4 import Dataset
import numpy as np

class exodus(object):
    '''
    Create an Exodus II file

    This is a simplified version of the official Exodus II python API,
    and contains only the functionality required by em2ex. It allows
    em2ex to be used even if Exodus isn't installed (by itself or as part
    of the SEACAS package).
    '''

    def __init__(self, file, mode='w', array_type='numpy', title=None,
                 numDims=None, numNodes=None, numElems=None, numBlocks=None,
                 numNodeSets=None, numSideSets=None):

        assert mode in ['w'], 'Mode must be w (to write)'
        assert array_type == 'numpy', 'array_type must be numpy'
        assert numDims in [1, 2, 3], 'numDims must be 1, 2 or 3'

        # Open the netCDF4 file for reading/writing
        self._rootgrp = Dataset(file, mode)

        if mode == 'w':
            # Write global attributes
            self._rootgrp.title = title
            self._rootgrp.version = np.float32(7.16)
            self._rootgrp.api_version = np.float32(7.16)
            self._rootgrp.floating_point_word_size = np.int32(8)
            self._rootgrp.maximum_name_length = np.int32(32)
            self._rootgrp.file_size = 1
            self._rootgrp.int64_status = 0

            # Create dimensions
            self._rootgrp.createDimension('len_string', 32)
            self._rootgrp.createDimension('len_name', 256)
            self._rootgrp.createDimension('num_dim', numDims)
            self._rootgrp.createDimension('num_nodes', numNodes)
            self._rootgrp.createDimension('num_elem', numElems)
            self._rootgrp.createDimension('num_el_blk', numBlocks)
            self._rootgrp.createDimension('time_step', None)

            # Create variables
            self._rootgrp.createVariable('time_whole', 'f8', 'time_step')
            self._rootgrp.createVariable('coor_names', 'S1', ('num_dim', 'len_name'))
            self._rootgrp.createVariable('coordx', 'f8', ('num_nodes'))
            self._rootgrp.createVariable('coordy', 'f8', ('num_nodes'))
            self._rootgrp.createVariable('coordz', 'f8', ('num_nodes'))
            self._rootgrp.createVariable('eb_status', 'i4', 'num_el_blk', fill_value = 0)
            self._rootgrp.createVariable('eb_prop1', 'i4', 'num_el_blk')
            self._rootgrp.variables['eb_prop1'].setncattr('name', 'ID')
            self._rootgrp.createVariable('eb_names', 'S1', ('num_el_blk', 'len_name'))


            if numSideSets:
                self._rootgrp.createDimension('num_side_sets', numSideSets)
                self._rootgrp.createVariable('ss_status', 'i4', 'num_side_sets', fill_value = 0)
                self._rootgrp.createVariable('ss_prop1', 'i4', 'num_side_sets')
                self._rootgrp.variables['ss_prop1'].setncattr('name', 'ID')
                self._rootgrp.createVariable('ss_names', 'S1', ('num_side_sets', 'len_name'))

            if numNodeSets:
                self._rootgrp.createDimension('num_node_sets', numNodeSets)
                self._rootgrp.createVariable('ns_status', 'i4', 'num_node_sets', fill_value = 0)
                self._rootgrp.createVariable('ns_prop1', 'i4', 'num_node_sets')
                self._rootgrp.variables['ns_prop1'].setncattr('name', 'ID')
                self._rootgrp.createVariable('ns_names', 'S1', ('num_node_sets', 'len_name'))

    def put_coord_names(self, names):

        num_dim = self._rootgrp.dimensions['num_dim'].size
        assert len(names) == num_dim, 'The length of the names array must be equal to the number of dimensions'

        for i in range(num_dim):
            self._rootgrp.variables['coor_names'][i, 0:len(names[i])] = [c for c in names[i]]

        return

    def put_coords(self, xcoords, ycoords, zcoords):

        assert len(xcoords) == self._rootgrp.dimensions['num_nodes'].size, 'Number of X coords must be equal to numNodes'
        assert len(ycoords) == self._rootgrp.dimensions['num_nodes'].size, 'Number of Y coords must be equal to numNodes'
        assert len(zcoords) == self._rootgrp.dimensions['num_nodes'].size, 'Number of Z coords must be equal to numNodes'

        self._rootgrp.variables['coordx'][:] = xcoords
        self._rootgrp.variables['coordy'][:] = ycoords
        self._rootgrp.variables['coordz'][:] = zcoords

        return

    def put_time(self, step, value):
        self._rootgrp.variables['time_whole'][step - 1] = value
        return

    def put_elem_blk_names(self, names):

        num_el_blk = self._rootgrp.dimensions['num_el_blk'].size
        assert len(names) == num_el_blk, 'The length of the names array must be equal to the number of blocks'

        for i in range(num_el_blk):
            self._rootgrp.variables['eb_names'][i, 0:len(names[i])] = [c for c in names[i]]

        return

    def put_elem_blk_info(self, blk_id, elem_type, num_blk_elems, num_elem_nodes, num_elem_attrs):

        assert num_elem_attrs == 0, 'No element attributes are used (num_elem_attrs must be 0)'

        # Find first free position in eb_status (first 0 value)
        eb_status = self._rootgrp.variables['eb_status']
        eb_status.set_auto_mask(False)
        idx = np.where(eb_status[:] == 0)[0][0]

        self._rootgrp.variables['eb_status'][idx] = 1
        self._rootgrp.variables['eb_prop1'][idx] = blk_id

        num_elem_in_blk_name = 'num_el_in_blk{}'.format(idx + 1)
        num_nodes_per_elem_name = 'num_nod_per_el{}'.format(idx + 1)
        self._rootgrp.createDimension(num_elem_in_blk_name, num_blk_elems)
        self._rootgrp.createDimension(num_nodes_per_elem_name, num_elem_nodes)

        var_name = 'connect{}'.format(idx + 1)
        self._rootgrp.createVariable(var_name, 'f8', (num_elem_in_blk_name, num_nodes_per_elem_name))
        self._rootgrp.variables[var_name].elem_type = str(elem_type).upper()

        return

    def put_elem_connectivity(self, blk_id, connectivity):

        assert blk_id in self._rootgrp.variables['eb_prop1'][:], 'blk_id not in list of block ids'

        # Get idx corresponding to blk_id
        idx = np.where(self._rootgrp.variables['eb_prop1'][:] == blk_id)[0][0]

        num_elem_in_blk_name = 'num_el_in_blk{}'.format(idx + 1)
        num_nodes_per_elem_name = 'num_nod_per_el{}'.format(idx + 1)
        num_elem_in_blk = self._rootgrp.dimensions[num_elem_in_blk_name].size
        num_nodes_per_elem = self._rootgrp.dimensions[num_nodes_per_elem_name].size
        assert connectivity.size == num_elem_in_blk * num_nodes_per_elem, 'Incorrect number of nodes in connectivity'

        var_name = 'connect{}'.format(idx + 1)
        self._rootgrp.variables[var_name][:] = connectivity.reshape(num_elem_in_blk, num_nodes_per_elem)

        return

    def put_side_set_names(self, names):

        num_side_sets = self._rootgrp.dimensions['num_side_sets'].size
        assert len(names) == num_side_sets, 'The length of the names array must be equal to the number of sidesets'

        for i in range(num_side_sets):
            self._rootgrp.variables['ss_names'][i, 0:len(names[i])] = [c for c in names[i]]

        return

    def put_node_set_names(self, names):

        num_node_sets = self._rootgrp.dimensions['num_node_sets'].size
        assert len(names) == num_node_sets, 'The length of the names array must be equal to the number of nodesets'

        for i in range(num_node_sets):
            self._rootgrp.variables['ns_names'][i, 0:len(names[i])] = [c for c in names[i]]

        return

    def put_side_set_params(self, id, num_side_set_elems, num_side_sets_dist_factor = 0):

        assert num_side_sets_dist_factor == 0, 'num_side_sets_dist_factor not used'
        assert id not in self._rootgrp.variables['ss_prop1'][:], 'Sideset id {} already in use'.format(id)

        # Find first free position in ss_status (first 0 value)
        ss_status = self._rootgrp.variables['ss_status']
        ss_status.set_auto_mask(False)
        idx = np.where(ss_status[:] == 0)[0][0]

        self._rootgrp.variables['ss_status'][idx] = 1
        self._rootgrp.variables['ss_prop1'][idx] = id

        num_side_ss_name = 'num_side_ss{}'.format(idx + 1)
        elem_ss_name = 'elem_ss{}'.format(idx + 1)
        side_ss_name = 'side_ss{}'.format(idx + 1)

        self._rootgrp.createDimension(num_side_ss_name, num_side_set_elems)
        self._rootgrp.createVariable(elem_ss_name, 'i4', num_side_ss_name)
        self._rootgrp.createVariable(side_ss_name, 'i4', num_side_ss_name)

        self._rootgrp.variables['ss_status'][idx] = 1
        self._rootgrp.variables['ss_prop1'][idx] = id

        return

    def put_node_set_params(self, id, num_node_set_nodes, num_node_sets_dist_factor = 0):

        assert num_node_sets_dist_factor == 0, 'num_node_sets_dist_factor not used'
        assert id not in self._rootgrp.variables['ns_prop1'][:], 'Nodeset id {} already in use'.format(id)

        # Find first free position in ss_status (first 0 value)
        ns_status = self._rootgrp.variables['ns_status']
        ns_status.set_auto_mask(False)
        idx = np.where(ns_status[:] == 0)[0][0]

        self._rootgrp.variables['ns_status'][idx] = 1
        self._rootgrp.variables['ns_prop1'][idx] = id

        num_node_ns_name = 'num_nod_ns{}'.format(idx + 1)
        node_ns_name = 'node_ns{}'.format(idx + 1)

        self._rootgrp.createDimension(num_node_ns_name, num_node_set_nodes)
        self._rootgrp.createVariable(node_ns_name, 'i4', num_node_ns_name)

        self._rootgrp.variables['ns_status'][idx] = 1
        self._rootgrp.variables['ns_prop1'][idx] = id

        return

    def put_side_set(self, id, side_set_elems, side_set_sides):

        assert id in self._rootgrp.variables['ss_prop1'][:], 'Sideset id {} not present'.format(id)

        # Get idx corresponding to id
        idx = np.where(self._rootgrp.variables['ss_prop1'][:] == id)[0][0]

        elem_ss_name = 'elem_ss{}'.format(idx + 1)
        side_ss_name = 'side_ss{}'.format(idx + 1)

        self._rootgrp.variables[elem_ss_name][:] = side_set_elems
        self._rootgrp.variables[side_ss_name][:] = side_set_sides

        return

    def put_node_set(self, id, node_set_nodes):

        assert id in self._rootgrp.variables['ns_prop1'][:], 'Nodeset id {} not present'.format(id)

        # Get idx corresponding to id
        idx = np.where(self._rootgrp.variables['ns_prop1'][:] == id)[0][0]

        node_ns_name = 'node_ns{}'.format(idx + 1)

        self._rootgrp.variables[node_ns_name][:] = node_set_nodes

        return

    def set_element_variable_number(self, number):

        self._rootgrp.createDimension('num_elem_var', number)
        self._rootgrp.createVariable('name_elem_var', 'S1', ('num_elem_var', 'len_name'))

        return

    def put_element_variable_name(self, name, index):

        self._rootgrp.variables['name_elem_var'][index - 1, 0:len(name)] = [c for c in name]
        return

    def get_element_variable_name(self):

        name_elem_var = self._rootgrp.variables['name_elem_var']
        name_elem_var.set_auto_mask(False)

        names = [b''.join(c).strip().decode() for c in name_elem_var[:]]
        return names

    def put_element_variable_values(self, blk_id, name, step, values):

        var_names = self.get_element_variable_name()
        block_ids = self._rootgrp.variables['eb_prop1'][:]
        assert name in var_names, 'Variable {} not found in list of element variables'.format(name)
        assert blk_id in block_ids, 'Block id {} not found'.format(blk_id)

        idx = np.where(block_ids == blk_id)[0][0]
        var_idx = var_names.index(name)

        var_name = 'vals_elem_var{}eb{}'.format(var_idx + 1, idx + 1)
        num_elem_in_blk = 'num_el_in_blk{}'.format(idx + 1)

        if var_name not in self._rootgrp.variables:
            self._rootgrp.createVariable(var_name, 'f8', ('time_step', num_elem_in_blk))

        self._rootgrp.variables[var_name][step - 1] = values

        return

    def set_node_variable_number(self, number):

        self._rootgrp.createDimension('num_nod_var', number)
        self._rootgrp.createVariable('name_nod_var', 'S1', ('num_nod_var', 'len_name'))

        return

    def put_node_variable_name(self, name, index):

        self._rootgrp.variables['name_nod_var'][index - 1, 0:len(name)] = [c for c in name]
        return

    def get_node_variable_name(self):

        name_node_var = self._rootgrp.variables['name_nod_var']
        name_node_var.set_auto_mask(False)

        names = [b''.join(c).strip().decode() for c in name_node_var[:]]

        return names

    def put_node_variable_values(self, name, step, values):

        var_names = self.get_node_variable_name()
        assert name in var_names, 'Variable {} not found in list of nodal variables'.format(name)

        var_idx = var_names.index(name)

        var_name = 'vals_nod_var{}'.format(var_idx + 1)

        if var_name not in self._rootgrp.variables:
            self._rootgrp.createVariable(var_name, 'f8', ('time_step', 'num_nodes'))

        self._rootgrp.variables[var_name][step - 1] = values

        return

    def set_side_set_variable_number(self, number):

        self._rootgrp.createDimension('num_sset_var', number)
        self._rootgrp.createVariable('name_sset_var', 'S1', ('num_sset_var', 'len_name'))

        return

    def put_side_set_variable_name(self, name, index):

        self._rootgrp.variables['name_sset_var'][index - 1, 0:len(name)] = [c for c in name]

        return

    def get_side_set_variable_name(self):

        name_side_set_var = self._rootgrp.variables['name_sset_var']
        name_side_set_var.set_auto_mask(False)

        names = [b''.join(c).strip().decode() for c in name_side_set_var[:]]

        return names

    def put_side_set_variable_values(self, id, name, step, values):

        var_names = self.get_side_set_variable_name()
        sideset_ids = self._rootgrp.variables['ss_prop1'][:]
        assert name in var_names, 'Variable {} not found in list of sideset variables'.format(name)
        assert id in sideset_ids, 'Sideset id {} not found'.format(id)

        idx = np.where(sideset_ids == id)[0][0]
        var_idx = var_names.index(name)

        var_name = 'vals_sset_var{}ss{}'.format(var_idx + 1, idx + 1)
        num_elem_in_ss = 'num_side_ss{}'.format(idx + 1)

        if var_name not in self._rootgrp.variables:
            self._rootgrp.createVariable(var_name, 'f8', ('time_step', num_elem_in_ss))

        self._rootgrp.variables[var_name][step - 1] = values

        return

    def set_node_set_variable_number(self, number):

        self._rootgrp.createDimension('num_nset_var', number)
        self._rootgrp.createVariable('name_nset_var', 'S1', ('num_nset_var', 'len_name'))

        return

    def put_node_set_variable_name(self, name, index):

        self._rootgrp.variables['name_nset_var'][index - 1, 0:len(name)] = [c for c in name]

        return

    def get_node_set_variable_name(self):

        name_node_set_var = self._rootgrp.variables['name_nset_var']
        name_node_set_var.set_auto_mask(False)

        names = [b''.join(c).strip().decode() for c in name_node_set_var[:]]

        return names

    def put_node_set_variable_values(self, id, name, step, values):

        var_names = self.get_node_set_variable_name()
        nodeset_ids = self._rootgrp.variables['ns_prop1'][:]
        assert name in var_names, 'Variable {} not found in list of nodeset variables'.format(name)
        assert id in nodeset_ids, 'Nodeset id {} not found'.format(id)

        idx = np.where(nodeset_ids == id)[0][0]
        var_idx = var_names.index(name)

        var_name = 'vals_nset_var{}ns{}'.format(var_idx + 1, idx + 1)
        num_nodes_in_ns = 'num_nod_ns{}'.format(idx + 1)

        if var_name not in self._rootgrp.variables:
            self._rootgrp.createVariable(var_name, 'f8', ('time_step', num_nodes_in_ns))

        self._rootgrp.variables[var_name][step - 1] = values

        return

    def close(self):
        self._rootgrp.close()
        return
