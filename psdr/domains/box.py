from __future__ import division

import numpy as np
from scipy.spatial.distance import pdist

from .domain import TOL
from .linineq import LinIneqDomain


class BoxDomain(LinIneqDomain):
	r""" Implements a domain specified by box constraints

	Given a set of lower and upper bounds, this class defines the domain

	.. math::

		\mathcal{D} := \lbrace \mathbf{x} \in \mathbb{R}^m : \text{lb} \le \mathbf{x} \le \text{ub} \rbrace \subset \mathbb{R}^m.

	Parameters
	----------
	lb: array-like (m,)
		Lower bounds
	ub: array-like (m,)
		Upper bounds
	"""
	def __init__(self, lb, ub, names = None):
		LinIneqDomain.__init__(self, lb = lb, ub = ub, names = names)	
		assert np.all(np.isfinite(lb)) and np.all(np.isfinite(ub)), "Both lb and ub must be finite to construct a box domain"

	# Due to the simplicity of this domain, we can use a more efficient sampling routine
	def _sample(self, draw = 1):
		x_sample = np.random.uniform(self.lb, self.ub, size = (draw, len(self)))
		return x_sample

	def _corner(self, p, **kwargs):
		# Since the domain is a box, we can find the corners simply by looking at the sign of p
		x = np.copy(self.lb)
		I = (p>=0)
		x[I] = self.ub[I]
		return x

	def _extent(self, x, p):
		return self._extent_bounds(x, p)

	def _isinside(self, X, tol = TOL):
		return self._isinside_bounds(X, tol = tol)

	def _normalized_domain(self, **kwargs):
		names_norm = [name + ' (normalized)' for name in self.names]
		return BoxDomain(lb = self.lb_norm, ub = self.ub_norm, names = names_norm)

	@property
	def A(self): return np.zeros((0,len(self)))
	
	@property
	def b(self): return np.zeros((0))
	
	@property
	def A_eq(self): return np.zeros((0,len(self)))
	
	@property
	def b_eq(self): return np.zeros((0))
