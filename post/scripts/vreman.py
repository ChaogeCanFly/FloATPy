#!/gpfs/mira-home/kmatsuno/floatpy_env/bin/python
from mpi4py import MPI
import numpy as np
import os
import sys

import floatpy.derivatives.compact.compact_derivative as cd
import floatpy.readers.padeops_reader as por
import floatpy.readers.parallel_reader as pdr
import floatpy.utilities.reduction as red
import statistics as stats
import get_namelist as nml
from SettingLib import NumSetting
from decorr_lscale_y import transpose2y
from common import *
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: "
        print "  python {} <prefix> [tID_start(default=0)] ".format(sys.argv[0])
        sys.exit()
    filename_prefix = sys.argv[1]
    start_index = 0
    if len(sys.argv) > 2:
        tID_list = map(int, sys.argv[2].strip('[]').split(',')) 
    else: tID_list = None

    periodic_dimensions = (True,False,True)
    x_bc = (0,0)
    y_bc = (0,0)
    z_bc = (0,0)

    comm  = MPI.COMM_WORLD
    rank  = comm.Get_rank()
    procs = comm.Get_size()

    # Set up the serial Miranda reader
    # Set up the parallel reader
    # Set up the reduction object
    serial_reader = por.PadeopsReader(filename_prefix, 
            periodic_dimensions=periodic_dimensions)
    reader = pdr.ParallelDataReader(comm, serial_reader)
    avg = red.Reduction(reader.grid_partition, periodic_dimensions)
    steps = sorted(reader.steps)
    if tID_list is None: tID_list = steps

    # Set up the derivative object
    x, y, z = reader.readCoordinates()
    dx,dy,dz = grid_res(x,y,z)
    der = cd.CompactDerivative(reader.grid_partition, 
            (dx, dy, dz), (10, 10, 10), periodic_dimensions)

    # setup the inputs object, get grid info
    dirname = os.path.dirname(filename_prefix)
    Nx,Ny,Nz,Lx,Ly,Lz = nml.read_grid_params(dirname,verbose=(rank==0))
    Ny = int(Ny)
    inp = nml.inputs(dirname,verbose=(rank==0))
    du = inp.du
    settings = NumSetting( comm, reader.grid_partition, 
             NX=Nx, NY=Ny, NZ=Nz,
             XMIN=0,        XMAX=Lx,
             YMIN=-Ly/2.,   YMAX=Ly/2.,
             ZMIN=0,        ZMAX=Lz,
             order=10)

    # Compute stats at each step:
    for tID in tID_list: 
        reader.step = tID
        
        # density and streamwise vel, means
        r, u, v, w, p = reader.readData( ('rho','u','v','w','p') )
        if (procs>1) and (np.shape(r)[1]<Ny): 
            if rank==0: print('Transposing')
            r = transpose2y(settings,r)
            u = transpose2y(settings,u)
            v = transpose2y(settings,v)
            w = transpose2y(settings,w)
            p = transpose2y(settings,p)
            if rank==0: print('Done')
        rbar = stats.reynolds_average(avg,r)
        utilde = stats.favre_average(avg,r,u,rho_bar=rbar)
        vtilde = stats.favre_average(avg,r,v,rho_bar=rbar)
        upp = u - utilde
        vpp = v - vtilde

        if rank==0: print('Computing viscous stress tensor')
        dudx,dudy,dudz = der.gradient(u, x_bc=x_bc, y_bc=y_bc, z_bc=z_bc)
        dudy_tilde = stats.favre_average(avg,r,dudy,rho_bar=rbar)
        sig11 = 2*dudx
        sig12 = dudy
        sig13 = dudz
        dudy,dudz=None,None
        dvdx,dvdy,dvdz = der.gradient(u, x_bc=x_bc, y_bc=y_bc, z_bc=z_bc)
        sig12 += dvdx
        sig22 = 2*dvdy
        sig23 = dvdz
        dvdx,dvdz = None,None
        dwdx,dwdy,dwdz = der.gradient(u, x_bc=x_bc, y_bc=y_bc, z_bc=z_bc)
        sig13 += dwdx
        sig23 += dwdy
        dwdx,dwdy = None,None
        
        div23 = 2./3.*(dudx+dvdy+dwdz)
        dudx,dvdy,dwdz = None,None,None
        sig11 = 1./inp.Re*(sig11-div23)
        sig12 /= inp.Re
        sig13 /= inp.Re
        sig22 = 1./inp.Re*(sig22-div23)
        sig23 /= inp.Re

        dudx_pp,dudy_pp,dudz_pp = der.gradient(upp, x_bc=x_bc, y_bc=y_bc, z_bc=z_bc)
        dvdx_pp,dvdy_pp,dvdz_pp = der.gradient(vpp, x_bc=x_bc, y_bc=y_bc, z_bc=z_bc)
        diss = sig11*dvdx_pp + sig12*(dvdy_pp+dudx_pp) + sig13*dvdz_pp + sig22*dudx_pp + sig23*dudz_pp
        D12 = stats.reynolds_average(diss)
        if rank==0: print('Done computing viscous dissipation')

        R12 = stats.favre_average(avg,r,upp*vpp,rho_bar=rbar)
        P12 = -rbar*R12*dudy_tilde
        Pi12= stats.reynolds_average(avg,p*(dudy_pp+dvdx_pp))

        dat = np.zeros([Ny,6],dtype='f')
        dat[:,0] = np.squeeze(stats.reynolds_average(avg,up*up))
        dat[:,1] = np.squeeze(stats.reynolds_average(avg,up*vp))
        dat[:,2] = np.squeeze(stats.reynolds_average(avg,up*wp))
        dat[:,3] = np.squeeze(stats.reynolds_average(avg,vp*vp))
        dat[:,4] = np.squeeze(stats.reynolds_average(avg,vp*wp))
        dat[:,5] = np.squeeze(stats.reynolds_average(avg,wp*wp))

        if rank==0: 
            dir_out = dirname.split('/lus/theta-fs0/projects/HighMachTurbulence/ShearLayerData/mira/')[-1]
            dir_out = '/home/kmatsuno/ShearLayerData/production/' + dir_out + '/'
            outputfile = dir_out+"vreman_%04d.dat"%tID
            print("Writing to {}".format(outputfile))
            np.savetxt(outputfile,np.squeeze(dat),delimiter=' ')
            print('Done')
