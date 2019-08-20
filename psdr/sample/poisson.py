from __future__ import print_function, division
import numpy as np
import itertools
from scipy.spatial.distance import cdist

def poisson_disk_sample(domain, r, L = None, Ntries = 100, grid = False):
	r""" Implements a Poisson disk sampling on an arbitrary domain


	Parameters
	----------
	domain: Domain
		Domain on which to construct the sampling 
	r: float, positive
		Minimum separation between points
	"""


	if L is None:
		L = np.eye(len(domain))


	# Use the grid approach to limit searches
	# https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf
	try:
		if grid is False:
			raise MemoryError
		# This radius is chosen so that no more than one point is in each grid cell
		grid_size = r/np.sqrt(L.shape[0])
		grid_start = np.zeros(L.shape[0])
		grid_dims = np.zeros(L.shape[0], dtype = np.int)
		for i in range(L.shape[0]):
			c1 = domain.corner(L[i,:])
			c2 = domain.corner(-L[i,:])
			if L[i,:].dot(c1) > L[i,:].dot(c2):
				c1, c2 = c2, c1
			grid_start[i] = L[i,:].dot(c1)
			grid_dims[i] = int(np.ceil((L[i,:].dot(c2) - L[i,:].dot(c1))/grid_size))

		grid = np.zeros(grid_dims, dtype = np.uint32)
	except (MemoryError, ValueError):
		grid = None	

	def grid_coord(x):
		""" location of x on the grid"""
		Lx = L.dot(x)
		idx = np.floor((Lx - grid_start)/grid_size)
		return idx.astype(np.int)
	

	X = [domain.sample()]
	active = [True]
	if grid is not None:
		idx = grid_coord(X[0])
		print(idx)
		grid[tuple(idx)] = 1

	while True:
		# Pick a random active elemenit
		try:
			i = int(np.random.permutation(np.argwhere(active))[0])
		except IndexError:
			break
		success = False

		LX = L.dot(np.array(X).T).T
		for it in range(Ntries):
			# Generate a random direction
			p = domain.random_direction(X[i])
			p /= np.linalg.norm(L.dot(p))

			# TODO: Change distribution to sample annulus uniformly
			ri = np.random.uniform(r, 2*r)
	
			# Generate trial point
			xc = X[i] + ri*p

			if domain.isinside(xc):
				if grid is not None:
					# Although this is technically more efficient, traversing over neighbors in Python is expensive
					idxc = grid_coord(xc)
					neighbors = []
					grid_rad = int(2*np.ceil(np.sqrt(L.shape[0])))+1
					for idx in itertools.product(*[ (j+k for k in range(-grid_rad, grid_rad+1)) for j in idxc]):
						try:
							if min(idx) < 0: raise IndexError
							n = grid[idx]
							if n != 0:
								neighbors.append(n-1)
						except IndexError:
							pass
					if len(neighbors) > 0:
						d = cdist(L.dot(xc).reshape(1,-1), LX[neighbors])
					else:
						d = [2*r]
				else:
					d = cdist(L.dot(xc).reshape(1,-1), LX)
				
				if np.min(d) > r:
					X.append(xc)
					active.append(True)
					success = True
					if grid is not None:
						grid[tuple(idxc)] = len(X)
					break

		if not success:
			active[i] = False

	return np.array(X)
