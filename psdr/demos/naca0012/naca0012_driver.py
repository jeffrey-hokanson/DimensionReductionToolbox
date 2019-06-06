import numpy as np
import SU2
import SU2.run
import SU2.io
import SU2.run.interface
from SU2.io.config import Config
from SU2.io.tools import read_aerodynamics
from discrete_adjoint import discrete_adjoint
import subprocess, os, argparse
import shutil
workdir = '/workdir'
su2home = os.environ['SU2_HOME']


def driver(x, n_lower = 10, n_upper = 10, maxiter = 1000, adjoint = None):

	assert adjoint in [None, 'discrete']

	# Bumps exclude endpoints
	x_lower = np.linspace(0,1,n_lower+2)[1:-1]
	x_upper = np.linspace(0,1,n_upper+2)[1:-1]
	
	# Here we pull the demo config for inviscid NACA0012 included
	# in the SU2 QuickStart tutorial
	cfg = Config(os.path.join(su2home, 'QuickStart/inv_NACA0012.cfg'))
	#cfg = Config('inv_NACA0012.cfg')

	# Set the number of SU2 iterations
	cfg['EXT_ITER'] = maxiter
	
	# Set to use Hicks-Henne bump functions
	cfg['DV_MARKER'] = ['airfoil']
	cfg['DEFINITION_DV'] = {}
	cfg['DEFINITION_DV']['KIND'] = len(x)*['HICKS_HENNE']
	cfg['DEFINITION_DV']['SCALE'] = len(x)*[ 1.0 ]
	cfg['DEFINITION_DV']['MARKER'] = len(x)*[ ['airfoil'] ]
	cfg['DEFINITION_DV']['FFDTAG'] = len(x)*[ [ ] ]
	# lower surfaces, then upper 
	cfg['DEFINITION_DV']['PARAM'] =  [ [0, xi] for xi in x_lower] + [ [1, xi] for xi in x_upper] 
	cfg['DEFINITION_DV']['SIZE'] = n_lower + n_upper
	# Set the deformation values
	cfg['DV_VALUE_NEW'] = x.tolist()

	# Specify the input and output for deformation
	shutil.copy(os.path.join(su2home, 'QuickStart/mesh_NACA0012_inv.su2'), 
		os.path.join(workdir, 'mesh_NACA0012_inv.su2'))
	cfg['MESH_FILENAME'] = 'mesh_NACA0012_inv.su2'
	cfg['MESH_OUT_FILENAME'] = 'mesh_deformed.su2'

	# Writes the config without commments
	cfg.dump(os.path.join(workdir, 'deform.cfg'))
   
	deformation_out_status = subprocess.run(['SU2_DEF','deform.cfg'],cwd=workdir)
	
	# Change which mesh gets loaded 
	cfg['MESH_FILENAME'] = 'mesh_deformed.su2'
	cfg['MESH_OUT_FILENAME'] = 'mesh_output.su2'
	
	# Specify the quantities of interest for gradient computation	
	cfg['OBJECTIVE_FUNCTION'] = 'LIFT,DRAG'

	if adjoint is None:
		cfg.dump(os.path.join(workdir, 'flow.cfg'))
		cfd_solver_out_status = subprocess.run(['SU2_CFD','flow.cfg'],cwd=workdir)
	elif adjoint == 'discrete':
		print("DISCRETE")

		cfg.WRT_CSV_SOL = 'YES'
		cfg['GRADIENT_METHOD'] = 'DISCRETE_ADJOINT'
		cfg.dump(os.path.join(workdir, 'flow.cfg'))
		

		if True:
			cfd_solver_out_status = subprocess.run(['SU2_CFD','flow.cfg'],cwd=workdir)
			cfd_solver_out_status = subprocess.run(['SU2_CFD_AD','flow.cfg'],cwd=workdir)

			#cfg['RESTART_SOL'] = 'YES'	 # As per forums this allows reuse??? 
			# https://www.cfd-online.com/Forums/su2/199359-su2-drag-sensitivities.html

			# It seems you can't get lift and drag simultaneously
			# https://www.cfd-online.com/Forums/su2/164982-get-gradients-both-lift-drag.html	
			cfg['OBJECTIVE_FUNCTION'] = 'LIFT'
			cfg.dump(os.path.join(workdir, 'flow.cfg'))
			state = discrete_adjoint('flow.cfg', compute = True)
			grad_lift = state.GRADIENTS['LIFT']
			data = read_aerodynamics(os.path.join(workdir, 'history.dat'))
			print('lift', data['LIFT'])
			print('drag', data['DRAG'])
			
			cfg['OBJECTIVE_FUNCTION'] = 'DRAG'
			cfg.dump(os.path.join(workdir, 'flow.cfg'))
			state = discrete_adjoint('flow.cfg', compute = True)
			grad_drag = state.GRADIENTS['DRAG']
			grad = np.vstack([grad_lift, grad_drag])
			
			print('grad', grad)	

#		#cfg.NUMBER_PART = 0
#		#cfg.NZONES = 1
#		
#		# Forward solution
#		info = SU2.run.direct(cfg)
#
#		# Adjoint solution
#		info = SU2.run.adjoint(cfg)
#
#		# Compute projection
#		info = SU2.run.projection(cfg)
#		print(info.GRADIENTS)
#		#SU2.run.interface.DOT(cfg)
#		#grad_lift = SU2.io.read_gradients(cfg['GRAD_OBJFUNC_FILENAME'])	
#		#print('lift', grad_lift)	
#		#cfd_solver_out_status = subprocess.run(['SU2_CFD','flow.cfg'],cwd=workdir)
#		
#		# Adjoine t solution
#		#cfd_solver_out_status = subprocess.run(['SU2_CFD_AD','flow.cfg'],cwd=workdir)
#	
#		# project the flow field to yield the drag gradient 
#		cfg.dump(os.path.join(workdir, 'flow.cfg'))
#		#subprocess.run(['SU2_DOT', 'flow.cfg'], cwd=workdir)
#		#grad_lift = np.loadtxt('of_grad_cd.dat', skiprows=1,delimiter=',', usecols = [1]) 	
#		
#		#cfg['OBJECTIVE_FUNCTION'] = 'DRAG'
#		#cfg.dump(os.path.join(workdir, 'flow.cfg'))
#		#subprocess.run(['SU2_DOT', 'flow.cfg'], cwd=workdir)
#		#grad_drag = read_gradients(cfg['GRAD_OBJFUNC_FILENAME'])	
#	
#		#grad = np.vstack([grad_lift, grad_drag])
#		#print(grad)
#		#cfd_solver_out_status = subprocess.run(['python','/usr/local/bin/discrete_adjoint.py', '-f', 'flow.cfg'],cwd=workdir)
#		# read the gradient
#		#grad = np.loadtxt('of_grad_cd.dat', skiprows=1,delimiter=',', usecols = [1]) 	
	
	# Read lift/drag QoI
	data = read_aerodynamics(os.path.join(workdir, 'history.dat'))
	print('lift', data['LIFT'])
	print('drag', data['DRAG'])
	fx = np.array([data['LIFT'], data['DRAG']])

	if adjoint is None:
		return fx
	else:
		return fx, grad		
	 

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = 'Run SU2')
	parser.add_argument(dest = 'infile', type = str)
	parser.add_argument('--nlower', type=int, default=10) 
	parser.add_argument('--nupper', type=int, default=10) 
	parser.add_argument('--adjoint', type=str, default = None)
	args = parser.parse_args()

	# Load data
	infile = args.infile
	x = np.loadtxt(infile).flatten()
	n_lower = args.nlower
	n_upper = args.nupper
	adjoint = args.adjoint
	print("adjoint", adjoint, adjoint == 'discrete' )	
	if adjoint is None:
		fx = driver(x, n_lower, n_upper, adjoint = adjoint)	
	else:
		fx, grad = driver(x, n_lower, n_upper, adjoint = adjoint)

	outfile = os.path.splitext(infile)[0] + '.output'
	np.savetxt(outfile, fx)
	
	if adjoint is not None:
		outfile = os.path.splitext(infile)[0] + '_grad.output'
		np.savetxt(outfile, grad)