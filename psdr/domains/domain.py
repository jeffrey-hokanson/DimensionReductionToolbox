
TOL = 1e-5

DEFAULT_CVXPY_KWARGS = {
	'solver': 'CVXOPT',
	'reltol': 1e-10,
	'abstol' : 1e-10,
	'verbose': False,
	'kktsolver': 'robust', 
	'warm_start': True,
}

class Domain(object):
	r""" Abstract base class for arbitary domain shapes
	"""
	
	################################################################################
	# Note that the following properities of the domain really should be determined 
	# by the class name, except for the one annoying exception: the TensorProductDomain
	# which is a child of Domain. These functions are here to provide access to this
	# information independent of the domain name.
	################################################################################

	@property
	def is_linquad_domain(self):
		r""" Returns true if the domain is purely specified by linear equality/inequality and convex quadratic constraints
		"""
		return self._is_linquad_domain()

	# By default, we assume the domain is not in this class unless the child class explicitly corrects this
	def _is_linquad_domain(self):
		return False

	@property
	def is_linineq_domain(self):
		r""" Returns True if the domain is specified by linear equality/inqueality constraints
		"""
		return self._is_linineq_domain()
	
	def _is_linquad_domain(self):
		return False

	@property
	def is_box_domain(self):
		r""" Returns True if the domain is specified only by bound constraints on each variable
		"""
		return self._is_box_domain()

	def _is_box_domain(self):
		return False