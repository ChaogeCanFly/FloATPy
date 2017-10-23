import numpy
import os
import unittest

import floatpy.readers.miranda_reader as mir

class TestReaderMiranda(unittest.TestCase):
    
    def setUp(self):
        self.filename_prefix = os.path.join(os.path.dirname(__file__), 'test_data_miranda/plot.mir')
        self.reader = mir.MirandaReader(self.filename_prefix, periodic_dimensions=(False,True,True))

        self.lo = (0, 0, 0)
        self.hi = (319, 63, 0)
        self.reader.sub_domain = (self.lo, self.hi)
        self.reader.step = 0
    
    
    def testReadCoordinatesChunk(self):
        
        # Read full coordinates.
        
        self.reader.sub_domain = (0,0,0), \
            (self.reader.domain_size[0]-1, self.reader.domain_size[1]-1, self.reader.domain_size[2]-1)
        
        x, y, z = self.reader.readCoordinates()
        
        # Read chunked coordinates.
        
        self.reader.sub_domain = self.lo, self.hi
        x_c, y_c, z_c = self.reader.readCoordinates()
        
        # Check that the chunked coordinates are equal to the corresponding full coords.
        
        xerr = numpy.absolute(x[ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - x_c).max()
        yerr = numpy.absolute(y[ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - y_c).max()
        zerr = numpy.absolute(z[ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - z_c).max()
        
        self.assertEqual(xerr, 0., "Incorrect chunked coordinate data reader in x direction!")
        self.assertEqual(yerr, 0., "Incorrect chunked coordinate data reader in y direction!")
        self.assertEqual(zerr, 0., "Incorrect chunked coordinate data reader in z direction!")
    
    
    def testReadDataChunk(self):
        
        # Read full data.
        
        self.reader.sub_domain = (0,0,0), \
            (self.reader.domain_size[0]-1, self.reader.domain_size[1]-1, self.reader.domain_size[2]-1)
        
        rho,    = self.reader.readData('density')
        u, v, w = self.reader.readData(('velocity-0','velocity-1','velocity-2'))
        p,      = self.reader.readData('pressure')
        
        # Read in chunked data.
        
        self.reader.sub_domain = self.lo, self.hi
        rho_c,        = self.reader.readData('density')
        u_c, v_c, w_c = self.reader.readData(('velocity-0','velocity-1','velocity-2'))
        p_c,          = self.reader.readData('pressure')
        
        # x_c, y_c, z_c = self.reader.readCoordinates()
        # plt.imshow( numpy.transpose(rho_c[:,:,0]), extent=[x_c[0,0,0], x_c[-1,-1,0], y_c[0,0,0], y_c[-1,-1,0]], origin='lower', interpolation='lanczos', aspect=1. )
        # plt.colorbar()
        # plt.show()

        rerr = numpy.absolute(rho[ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - rho_c).max()
        uerr = numpy.absolute(u  [ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - u_c  ).max()
        verr = numpy.absolute(v  [ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - v_c  ).max()
        werr = numpy.absolute(w  [ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - w_c  ).max()
        perr = numpy.absolute(p  [ self.lo[0]:self.hi[0]+1, self.lo[1]:self.hi[1]+1, self.lo[2]:self.hi[2]+1 ] - p_c  ).max()
        
        self.assertEqual(rerr, 0., "Incorrect chunked variable data reader for rho!")
        self.assertEqual(uerr, 0., "Incorrect chunked variable data reader for u!")
        self.assertEqual(verr, 0., "Incorrect chunked variable data reader for v!")
        self.assertEqual(werr, 0., "Incorrect chunked variable data reader for w!")
        self.assertEqual(perr, 0., "Incorrect chunked variable data reader for p!")


if __name__ == '__main__':
    unittest.main()
