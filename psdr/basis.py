""" Descriptions of various bases"""

__all__ = ['PolynomialTensorBasis', 
	'MonomialTensorBasis', 
	'LegendreTensorBasis',
	'ChebyshevTensorBasis',
	'LaguerreTensorBasis',
	'HermiteTensorBasis',
	'ArnoldiPolynomialBasis',
 ]

import numpy as np
from numpy.polynomial.polynomial import polyvander, polyder, polyroots
from numpy.polynomial.legendre import legvander, legder, legroots 
from numpy.polynomial.chebyshev import chebvander, chebder, chebroots
from numpy.polynomial.hermite import hermvander, hermder, hermroots
from numpy.polynomial.laguerre import lagvander, lagder, lagroots

class Basis(object):
	pass



################################################################################
# Indexing utility functions for total degree
################################################################################

#TODO: Should these be moved into PolynomialTensorBasis class? 

def _full_index_set(n, d):
	""" A helper function for index_set.
	"""
	if d == 1:
		I = np.array([[n]])
	else:
		II = _full_index_set(n, d-1)
		m = II.shape[0]
		I = np.hstack((np.zeros((m, 1)), II))
		for i in range(1, n+1):
			II = _full_index_set(n-i, d-1)
			m = II.shape[0]
			T = np.hstack((i*np.ones((m, 1)), II))
			I = np.vstack((I, T))
	return I

def index_set(n, d):
	"""Enumerate multi-indices for a total degree of order `n` in `d` variables.
	
	Parameters
	----------
	n : int
		degree of polynomial
	d : int
		number of variables, dimension
	Returns
	-------
	I : ndarray
		multi-indices ordered as columns
	"""
	I = np.zeros((1, d), dtype = np.int)
	for i in range(1, n+1):
		II = _full_index_set(i, d)
		I = np.vstack((I, II))
	return I[:,::-1].astype(int)


class PolynomialTensorBasis(Basis):
	r""" Generic tensor product basis of fixed total degree

	This class constructs a tensor product basis of dimension :math:`n`
	of fixed given degree :math:`p` given a basis for polynomials
	in one variable. Namely, this basis is composed of elements:

	.. math::

		\psi_j(\mathbf x) := \prod_{i=1}^n \phi_{[\boldsymbol \alpha_j]_i}(x_i) 
			\quad \sum_{i=1}^n [\boldsymbol \alpha_j]_i \le p;
			\quad \phi_i \in \mathcal{P}_{i}(\mathbb{R})


	Parameters
	----------
	dim: int
		The input dimension of the space
	degree: int
		The total degree of polynomials
	polyvander: function
		Function providing the scalar Vandermonde matrix (i.e., numpy.polynomial.polynomial.polyvander)
	polyder: function
		Function providing the derivatives of scalar polynomials (i.e., numpy.polynomial.polynomial.polyder)	
 
	"""
	def __init__(self, dim, degree, polyvander, polyder):
		self.dim = int(dim)
		self.degree = int(degree)
		self.vander = polyvander
		self.der = polyder
		self.indices = index_set(self.degree, self.dim).astype(int)
		self._build_Dmat()

	def __len__(self):
		return len(self.indices)

	def _build_Dmat(self):
		""" Constructs the (scalar) derivative matrix
		"""
		self.Dmat = np.zeros( (self.degree+1, self.degree))
		for j in range(self.degree + 1):
			ej = np.zeros(self.degree + 1)
			ej[j] = 1.
			self.Dmat[j,:] = self.der(ej)

	def set_scale(self, X):
		r""" Construct an affine transformation of the domain to improve the conditioning
		"""
		self._set_scale(np.array(X))

	def _set_scale(self, X):
		r""" default scaling to [-1,1]
		"""
		self._lb = np.min(X, axis = 0)
		self._ub = np.max(X, axis = 0)

	def _scale(self, X):
		r""" Apply the scaling to the input coordinates
		"""
		try:
			return 2*(X-self._lb[None,:])/(self._ub[None,:] - self._lb[None,:]) - 1
		except AttributeError:
			return X

	def _dscale(self):
		r""" returns the scaling associated with the scaling transform
		"""
		try:
			return (2./(self._ub - self._lb))
		except AttributeError:
			raise NotImplementedError

	def V(self, X):
		r""" Builds the Vandermonde matrix associated with this basis

		Given points :math:`\mathbf x_i \in \mathbb{R}^n`, 
		this creates the Vandermonde matrix

		.. math::

			[\mathbf{V}]_{i,j} = \phi_j(\mathbf x_i)

		where :math:`\phi_j` is a multivariate polynomial as defined in the class definition.

		Parameters
		----------
		X: array-like (M, n)
			Points at which to evaluate the basis at where :code:`X[i]` is one such point in 
			:math:`\mathbf{R}^n`.
		
		Returns
		-------
		V: np.array
			Vandermonde matrix
		"""
		X = X.reshape(-1, self.dim)
		X = self._scale(np.array(X))
		M = X.shape[0]
		assert X.shape[1] == self.dim, "Expected %d dimensions, got %d" % (self.dim, X.shape[1])
		V_coordinate = [self.vander(X[:,k], self.degree) for k in range(self.dim)]
		
		V = np.ones((M, len(self.indices)), dtype = X.dtype)
		
		for j, alpha in enumerate(self.indices):
			for k in range(self.dim):
				V[:,j] *= V_coordinate[k][:,alpha[k]]
		return V

	def VC(self, X, c):
		r""" Evaluate the product of the Vandermonde matrix and a vector

		This evaluates the product :math:`\mathbf{V}\mathbf{c}`
		where :math:`\mathbf{V}` is the Vandermonde matrix defined in :code:`V`.
		This is done without explicitly constructing the Vandermonde matrix to save
		memory.	
		 
		Parameters
		----------
		X: array-like (M,n)
			Points at which to evaluate the basis at where :code:`X[i]` is one such point in 
			:math:`\mathbf{R}^n`.
		c: array-like 
			The vector to take the inner product with.
		
		Returns
		-------
		Vc: np.array (M,)
			Product of Vandermonde matrix and :math:`\mathbf c`
		"""
		X = X.reshape(-1, self.dim)
		X = self._scale(np.array(X))
		M = X.shape[0]
		c = np.array(c)
		assert len(self.indices) == c.shape[0]

		if len(c.shape) == 2:
			oneD = False
		else:
			c = c.reshape(-1,1)
			oneD = True

		V_coordinate = [self.vander(X[:,k], self.degree) for k in range(self.dim)]
		out = np.zeros((M, c.shape[1]))	
		for j, alpha in enumerate(self.indices):

			# If we have a non-zero coefficient
			if np.max(np.abs(c[j,:])) > 0.:
				col = np.ones(M)
				for ell in range(self.dim):
					col *= V_coordinate[ell][:,alpha[ell]]

				for k in range(c.shape[1]):
					out[:,k] += c[j,k]*col
		if oneD:
			out = out.flatten()
		return out

	def DV(self, X):
		r""" Column-wise derivative of the Vandermonde matrix

		Given points :math:`\mathbf x_i \in \mathbb{R}^n`, 
		this creates the Vandermonde-like matrix whose entries
		correspond to the derivatives of each of basis elements;
		i.e., 

		.. math::

			[\mathbf{V}]_{i,j} = \left. \frac{\partial}{\partial x_k} \psi_j(\mathbf{x}) 
				\right|_{\mathbf{x} = \mathbf{x}_i}.

		Parameters
		----------
		X: array-like (M, n)
			Points at which to evaluate the basis at where :code:`X[i]` is one such point in 
			:math:`\mathbf{R}^n`.

		Returns
		-------
		Vp: np.array (M, N, n)
			Derivative of Vandermonde matrix where :code:`Vp[i,j,:]`
			is the gradient of :code:`V[i,j]`. 
		"""
		X = X.reshape(-1, self.dim)
		X = self._scale(np.array(X))
		M = X.shape[0]
		V_coordinate = [self.vander(X[:,k], self.degree) for k in range(self.dim)]
		
		N = len(self.indices)
		DV = np.ones((M, N, self.dim), dtype = X.dtype)

		try:
			dscale = self._dscale()
		except NotImplementedError:
			dscale = np.ones(X.shape[1])	


		for k in range(self.dim):
			for j, alpha in enumerate(self.indices):
				for q in range(self.dim):
					if q == k:
						DV[:,j,k] *= np.dot(V_coordinate[q][:,0:-1], self.Dmat[alpha[q],:])
					else:
						DV[:,j,k] *= V_coordinate[q][:,alpha[q]]
			# Correct for transform
			DV[:,:,k] *= dscale[k] 		

		return DV
	
	def DDV(self, X):
		r""" Column-wise second derivative of the Vandermonde matrix

		Given points :math:`\mathbf x_i \in \mathbb{R}^n`, 
		this creates the Vandermonde-like matrix whose entries
		correspond to the derivatives of each of basis elements;
		i.e., 

		.. math::

			[\mathbf{V}]_{i,j} = \left. \frac{\partial^2}{\partial x_k\partial x_\ell} \psi_j(\mathbf{x}) 
				\right|_{\mathbf{x} = \mathbf{x}_i}.

		Parameters
		----------
		X: array-like (M, n)
			Points at which to evaluate the basis at where :code:`X[i]` is one such point in 
			:math:`\mathbf{R}^m`.

		Returns
		-------
		Vpp: np.array (M, N, n, n)
			Second derivative of Vandermonde matrix where :code:`Vpp[i,j,:,:]`
			is the Hessian of :code:`V[i,j]`. 
		"""
		X = X.reshape(-1, self.dim)
		X = self._scale(np.array(X))
		M = X.shape[0]
		V_coordinate = [self.vander(X[:,k], self.degree) for k in range(self.dim)]
		
		N = len(self.indices)
		DDV = np.ones((M, N, self.dim, self.dim), dtype = X.dtype)

		try:
			dscale = self._dscale()
		except NotImplementedError:
			dscale = np.ones(X.shape[1])	


		for k in range(self.dim):
			for ell in range(k, self.dim):
				for j, alpha in enumerate(self.indices):
					for q in range(self.dim):
						if q == k == ell:
							# We need the second derivative
							eq = np.zeros(self.degree+1)
							eq[alpha[q]] = 1.
							der2 = self.der(eq, 2)
							DDV[:,j,k,ell] *= V_coordinate[q][:,0:len(der2)].dot(der2)
						elif q == k or q == ell:
							DDV[:,j,k,ell] *= np.dot(V_coordinate[q][:,0:-1], self.Dmat[alpha[q],:])
						else:
							DDV[:,j,k,ell] *= V_coordinate[q][:,alpha[q]]

				# Correct for transform
				DDV[:,:,k, ell] *= dscale[k]*dscale[ell]
				DDV[:,:,ell, k] = DDV[:,:,k, ell]
		return DDV

	def roots(self, coef):
		if self.dim > 1:
			raise NotImplementedError
		r = legroots(coef)
		return r*(self._ub[0] - self._lb[0])/2.0 + (self._ub[0] + self._lb[0])/2.
		 

class MonomialTensorBasis(PolynomialTensorBasis):
	"""A tensor product basis of bounded total degree built from the monomials"""
	def __init__(self, dim, degree):
		PolynomialTensorBasis.__init__(self, dim, degree, polyvander, polyder)
	
	def roots(self, coef):
		if self.dim > 1:
			raise NotImplementedError
		r = polyroots(coef)
		return r*(self._ub[0] - self._lb[0])/2.0 + (self._ub[0] + self._lb[0])/2.
	
class LegendreTensorBasis(PolynomialTensorBasis):
	"""A tensor product basis of bounded total degree built from the Legendre polynomials

	"""
	def __init__(self, dim, degree):
		PolynomialTensorBasis.__init__(self, dim, degree, legvander, legder)

class ChebyshevTensorBasis(PolynomialTensorBasis):
	"""A tensor product basis of bounded total degree built from the Chebyshev polynomials
	
	"""
	def __init__(self, dim, degree):
		PolynomialTensorBasis.__init__(self, dim, degree, chebvander, chebder)
	
	def roots(self, coef):
		if self.dim > 1:
			raise NotImplementedError
		r = chebroots(coef)
		return r*(self._ub[0] - self._lb[0])/2.0 + (self._ub[0] + self._lb[0])/2.

class LaguerreTensorBasis(PolynomialTensorBasis):
	"""A tensor product basis of bounded total degree built from the Laguerre polynomials

	"""
	def __init__(self, dim, degree):
		PolynomialTensorBasis.__init__(self, dim, degree, lagvander, lagder)
	
	def roots(self, coef):
		if self.dim > 1:
			raise NotImplementedError
		r = lagroots(coef)
		return r*(self._ub[0] - self._lb[0])/2.0 + (self._ub[0] + self._lb[0])/2.

class HermiteTensorBasis(PolynomialTensorBasis):
	"""A tensor product basis of bounded total degree built from the Hermite polynomials

	"""
	def __init__(self, dim, degree):
		PolynomialTensorBasis.__init__(self, dim, degree, hermvander, hermder)

	def _set_scale(self, X):
		self._mean = np.mean(X, axis = 0)
		self._std = np.std(X, axis = 0)

	def _scale(self, X):
		try:
			return (X - self._mean[None,:])/self._std[None,:]/np.sqrt(2)
		except AttributeError:
			return X

	def _dscale(self):
		try:
			return 1./self._std/np.sqrt(2)
		except AttributeError:
			raise NotImplementedError

	def roots(self, coef):
		if self.dim > 1:
			raise NotImplementedError
		r = hermroots(coef)
		return r*self._std[0]*np.sqrt(2) + self._mean[0]


class ArnoldiPolynomialBasis(Basis):
	r""" Construct a stable polynomial basis for arbitrary points using Vandermonde+Arnoldi
	"""
	def __init__(self, X, degree):
		self.X = np.copy(np.atleast_2d(X))
		self.dim = self.X.shape[1]
		self.degree = int(degree)
		self.idx = index_set(self.degree, self.dim)

		self.Q, self.R = self.arnoldi()

	def _update_vec(self, ids):
		# Determine which column to multiply by
		diff = self.idx - ids
		# Here we pick the most recent column that is one off
		j = np.max(np.argwhere( (np.sum(np.abs(diff), axis = 1) <= 1) & (np.min(diff, axis = 1) == -1)))
		i = int(np.argwhere(diff[j] == -1))
		return i, j	

	def arnoldi(self):
		r""" Apply the Arnoldi proceedure to build up columns of the Vandermonde matrix
		"""
		idx = self.idx
		M = self.X.shape[0]

		# Allocate memory for matrices
		Q = np.zeros((M, len(idx)))
		R = np.zeros((len(idx), len(idx)))
	
		# Generate columns of the Vandermonde matrix
		iteridx = enumerate(idx)
		# As the first column is the ones vector, we treat it as a special case
		next(iteridx)
		Q[:,0] = 1/np.sqrt(M)
		R[0,0] = np.sqrt(M)	

		# Now work on the remaining columns
		for k, ids in iteridx:
			i, j = self._update_vec(ids) 
			# Form new column
			q = self.X[:,i] * Q[:,j]
	
			for j in range(k):
				R[j,k] = Q[:,j].T @ q/M
				q -= R[j,k]*Q[:,j]
			
			R[k,k] = np.linalg.norm(q)
			Q[:,k] = q/R[k,k]

		return Q, R

	def arnoldi_X(self, X):
		r""" Generate a Vandermonde matrix corresponding to a different set of points
		"""
		M = self.Q.shape[0]	
		iteridx = enumerate(self.idx)
		# As the first column is the ones vector, we treat it as a special case
		next(iteridx)
		W = np.zeros(self.Q.shape, dtype = self.Q.dtype)
		W[:,0] = 1/np.sqrt(M)

		# Now work on the remaining columns
		for k, ids in iteridx:
			i, j = self._update_vec(ids) 
			# Form new column
			w = self.X[:,i] * W[:,j]
	
			for j in range(k):
				w -= self.R[j,k]*W[:,j]
			
			W[:,k] = w/self.R[k,k]

		return W
		

	def V(self, X = None):
		if X is None or np.all(X == self.X):
			return self.Q
		else:
			return self.arnoldi_X(X)


	def DV(self, X = None):
		if X is None or np.all(X == self.X):
			V = self.Q
		else:
			V = self.arnoldi_X(X)

		M, N = self.Q.shape
		n = self.X.shape[1]
		DV = np.zeros((M, N, n), dtype = self.Q.dtype)

		for k in range(n):
			for j, ids in enumerate(self.idx):
				# now apply the chain rule recursively
				ids = np.copy(ids)
				ids[k] -= 1
				if np.min(ids) >= 0:
					i = int(np.argwhere([np.all(idx == ids) for idx in self.idx]).flatten())
					DV[:,j,k] = V[:,i] + DV[:,i,k]
		
		return DV

