from scipy.spatial import cKDTree
import numpy as np
import matplotlib.pyplot as plt
from astropy.convolution import convolve, convolve_fft, Gaussian2DKernel
from astropy.modeling.models import Sersic2D

from astropy.io import fits

from ..core import * 

import FLARE.filters 





def physical(X, Y, luminosities, filters, resolution = 0.1, Ndim = 100, smoothing = False, smoothing_parameter = False):

    return {f: physical_individual(X, Y, luminosities[f], resolution = resolution, Ndim = Ndim, smoothing = smoothing, smoothing_parameter = smoothing_parameter) for f in filters}
    

class physical_individual():

    def __init__(self, X, Y, L, resolution = 0.1, Ndim = 100, smoothing = False, smoothing_parameter = False):

        self.warnings = []

        # Centre star particle positions using the median as the centre *** NOTE: true centre could later be defined ***
        X -= np.median(X)
        Y -= np.median(Y)

        # Boolean = Whether to apply gaussian smoothing to star particles
        self.smoothing = smoothing
        self.smoothing_parameter = smoothing_parameter

        # Image properties
        self.Ndim = Ndim
        self.resolution = resolution
        self.width = Ndim * resolution 

        range = [np.max(X) - np.min(X), np.max(Y) - np.min(Y)]

        if any(x>Ndim*resolution for x in range): self.warnings.append('Warning particles will extend beyond image limits')

                

        self.data = np.zeros((self.Ndim, self.Ndim))

        # --- exclude particles not inside the image area
        
        sel = (np.fabs(X)<self.width/2.)&(np.fabs(Y)<self.width/2.)
        
        X = X[sel]
        Y = Y[sel]
        L = L[sel]

        if self.smoothing == 'gaussian':
        
            Gx, Gy = np.meshgrid(np.linspace(-(self.width+self.resolution)/2., (self.width+self.resolution)/2., Ndim+1), np.linspace(-(self.width+self.resolution)/2., (self.width+self.resolution)/2., Ndim+1))
        
            sigma = self.smoothing_parameter/2.355
            
            gauss = np.exp(-((Gx**2 + Gy**2)/ ( 2.0 * sigma**2 ) ) )  
            gauss /= np.sum(gauss)
            
            g = np.linspace(-self.width/2.,self.width/2.,Ndim)
        
            for x,y,l in zip(X, Y, L):
        
                i, j = (np.abs(g - x)).argmin(), (np.abs(g - y)).argmin()
        
                self.data[j,i] += l
                
            self.data = convolve_fft(self.data, gauss)
            
            

        elif self.smoothing == 'adaptive':
         
            Gx, Gy = np.meshgrid(np.linspace(-self.width/2., self.width/2., Ndim), np.linspace(-self.width/2., self.width/2., Ndim))

            tree = cKDTree(np.column_stack([X, Y]), leafsize=16, compact_nodes=True, copy_data=False, balanced_tree=True)

            nndists, nninds = tree.query(np.column_stack([X, Y]), k=self.smoothing_parameter, n_jobs=-1) # k = nth nearest neighbour
        
            for x,y,l,nndist in zip(X, Y, L, nndists):
    
                FWHM = np.max([nndist[-1], self.resolution/2.])
                
                sigma = FWHM/2.355
                   
                gauss = np.exp(-(((Gx - x)**2 + (Gy - y)**2)/ ( 2.0 * sigma**2 ) ) )  

                sgauss = np.sum(gauss)

                if sgauss > 0: self.data += l*gauss/sgauss


        elif self.smoothing == False:
             
            g = np.linspace(-self.width/2.,self.width/2.,Ndim)
        
            for x,y,l in zip(X, Y, L):
        
                i, j = (np.abs(g - x)).argmin(), (np.abs(g - y)).argmin()
        
                self.data[j,i] += l















def observed(X, Y, fluxes, filters, cosmo, redshift, width = 10., resampling_factor = False, pixel_scale = False, smoothed = False, PSFs = None):

    xoffset = np.random.random() - 0.5 # offset in pixels
    yoffset = np.random.random() - 0.5 # offset in pixels

    return {f: observed_individual(X, Y, fluxes[f], f, cosmo, redshift, width = width, resampling_factor = resampling_factor, pixel_scale = pixel_scale, smoothed = smoothed, PSF = PSFs[f], xoffset = xoffset, yoffset = yoffset) for f in filters}


def observed_individual(X, Y, flux, filter, cosmo, redshift, width=10., resampling_factor=False, pixel_scale=False, smoothed=False, PSF = None, xoffset = 0.0, yoffset = 0.0):

    X -= - np.median(X) 
    Y -= - np.median(Y) 
    
    arcsec_per_proper_kpc = cosmo.arcsec_per_kpc_proper(redshift).value
    
    X_arcsec = X * arcsec_per_proper_kpc
    Y_arcsec = Y * arcsec_per_proper_kpc
    
    return observed_frame(X_arcsec, Y_arcsec, flux, filter, width=width, resampling_factor=resampling_factor, pixel_scale=pixel_scale, smoothed=smoothed, PSF = PSF, xoffset = xoffset, yoffset = yoffset)





def point_sources(fluxes, filters, width=10., resampling_factor=False, pixel_scale=False, smoothed=False, PSFs = None):

    xoffset = np.random.random() - 0.5
    yoffset = np.random.random() - 0.5

    return {f: observed_frame(np.array([0.0]), np.array([0.0]), fluxes[f], f, width, resampling_factor, pixel_scale, smoothed, PSFs[f], xoffset = xoffset, yoffset = yoffset) for f in filters}


def point_source(flux, filter, width=10., resampling_factor=False, pixel_scale=False, smoothed=False, PSF = None, xoffset = 0.0, yoffset = 0.0):

    return observed_frame(np.array([0.0]),np.array([0.0]), flux, filter, width, resampling_factor, pixel_scale, smoothed, PSF, xoffset = xoffset, yoffset = yoffset)
    
    





class observed_TEST():

    def __init__(self, X_arcsec, Y_arcsec, flux, filter, width=10., resampling_factor = False, pixel_scale = False, PSF = None, xoffset = 0.0, yoffset = 0.0):
    
        self.warnings = []

        self.base_pixel_scale = FLARE.filters.pixel_scale[filter]

        self.width = width # target width in " 
        
        if resampling_factor:
            self.pixel_scale = self.base_pixel_scale / resampling_factor # the actual resolution 
            self.resampling_factor = resampling_factor
        elif pixel_scale:
            self.pixel_scale = pixel_scale
            self.resampling_factor = self.base_pixel_scale/self.pixel_scale
        else:
            self.pixel_scale = self.base_pixel_scale
            self.resampling_factor = 1.0
        
        self.Ndim = round(self.width / self.pixel_scale)
        self.actual_width = self.Ndim *  self.pixel_scale # actual width "
        self.PSF = PSF # PSF object


        self.X_arcsec = X_arcsec
        self.Y_arcsec = Y_arcsec
        
        self.X_pix = self.X_arcsec/self.pixel_scale + xoffset # offset's are necessary so that the object doesn't in the middle of a pixel
        self.Y_pix = self.Y_arcsec/self.pixel_scale + yoffset # offset's are necessary so that the object doesn't in the middle of a pixel
        
        inst = filter.split('.')[1]
        f = filter.split('.')[-1]
        
        self.flux = flux
    
     
    def Sersic(self, p):
    

    
        # --- unlike the other routines this works by convolving the intrinsic Sersic image with the PSF
    
        x = y = np.linspace(-(self.Ndim/2.-0.5), (self.Ndim/2.-0.5), self.Ndim)
        
        xx, yy = np.meshgrid(x, y)        
    
        mod = Sersic2D(amplitude = 1, r_eff = p['r_eff'], n = p['n'], x_0 = self.X_pix, y_0 = self.Y_pix, ellip = p['ellip'], theta = p['theta'])
        
        sersic = mod(xx, yy)
        
        sersic /= np.sum(sersic)
        
        psf = self.PSF.f(x/self.resampling_factor, y/self.resampling_factor)
    
        psf /= np.sum(psf)
        
        image = empty()
    
        image.img = convolve(self.flux * sersic, psf)
        
        return image        










    
    
    
    
    

class observed_frame():
    """ A class for computing synthetic Webb observations. 
    """
    
    def __init__(self, X_arcsec, Y_arcsec, flux, filter, width=10., resampling_factor=False, pixel_scale=False, smoothed=False, PSF = None, xoffset = 0.0, yoffset = 0.0):
        
        """
        :param X: Star Particle X position in kpc. [nStar]
        :param Y: Star Particle Y position in kpc. [nStar]
        :param flux: An array of flux for each star particle for each filter in nJy. [nStar, nnircfilter]
        :param nircfilter: Either a string of the form JWST.NIRCam.XXXXX, where XXXXX is the desired filter code
        or the FWHM of the gaussian PSF (float).
        :param width: Width of the image along a single axis (this is approximate since images must be odd in dimension)
        :param resampling_factor: The integer amount of resampling done to increase resolution. (int)
        :param smoothed: Boolean, whether to apply smoothing.
        :param PSF: Instance of the webbPSFs object for the desired filter .
        :param show: Boolean, whether to show images.
        """

        self.warnings = []

        self.base_pixel_scale = FLARE.filters.pixel_scale[filter]

        self.width = width # target width in " 
        
        if resampling_factor:
            self.pixel_scale = self.base_pixel_scale / resampling_factor # the actual resolution 
            self.resampling_factor = resampling_factor
        elif pixel_scale:
            self.pixel_scale = pixel_scale
            self.resampling_factor = self.base_pixel_scale/self.pixel_scale
            # self.resampling_factor = 1.0
        else:
            self.pixel_scale = self.base_pixel_scale
            self.resampling_factor = 1.0
        
        self.Ndim = round(self.width / self.pixel_scale)
        self.actual_width = self.Ndim *  self.pixel_scale # actual width "
        self.PSF = PSF # PSF object


        self.X_arcsec = X_arcsec
        self.Y_arcsec = Y_arcsec
        
        self.X_pix = self.X_arcsec/self.pixel_scale + xoffset # offset's are necessary so that the object doesn't in the middle of a pixel
        self.Y_pix = self.Y_arcsec/self.pixel_scale + yoffset # offset's are necessary so that the object doesn't in the middle of a pixel
        
        
        inst = filter.split('.')[1]
        f = filter.split('.')[-1]
        
        self.smoothed = smoothed

        self.flux = flux

#        
#         # Get the range of x and y star particle positions
#         pos_range = [np.max(X) - np.min(X), np.max(Y) - np.min(Y)]
# 
#         # If star particles extend beyond the image print a warning
#         if any(x > self.actual_width for x in pos_range): self.warnings.append('Warning particles will extend beyond image limits')
# 

        # --- there are now 3 possible options
        
        if self.PSF is not None:

            # --- THIS NEEDS RE-WRITING BY **WILL**   

#             self.simple_img = self.simpleimg()
#             self.img = self.smoothimg(self.PSF.f)
#             self.img2 = self.smoothimg2(self.PSF.f)
            self.img3 = self.smoothimg3(self.PSF.f)
       
        else:


            # If smoothing is required compute the smoothed image for each filter
            if self.smoothed:

                self.img = self.smoothimg() # need to give it a smoothing function

            # If smoothing is not required compute the simple images
            else:

                self.img = self.simpleimg()

        
    def simpleimg(self):
        """ A method for creating simple images where the stars are binned based on their position.

        :param F: The flux array for the current filter
        :return: Image array
        """

        # Initialise the image array
        simple_img = np.zeros((self.Ndim, self.Ndim))

        # Get the image pixel coordinates
        g = np.linspace(-self.width / 2., self.width / 2., self.Ndim)

        # Loop through star particles
        for x, y, l in zip(self.X_arcsec, self.Y_arcsec, self.flux):

            # Get the stars position within the image
            i, j = (np.abs(g - x)).argmin(), (np.abs(g - y)).argmin()

            # Add the flux of this star to the corresponding pixel
            simple_img[j, i] += l

        return simple_img


    def smoothimg(self, f):

        

        image = np.zeros((self.Ndim, self.Ndim))

        xx = yy = np.arange(-self.Ndim/2.+0.5, self.Ndim/2., 1.)  # in original pixels

        for x, y, l in zip(self.X_pix, self.Y_pix, self.flux):

            # Get this star's position within the image
            
            g = f((xx-x)/self.resampling_factor, (yy-y)/self.resampling_factor)
            
            g /= np.sum(g)
            
            image += l * g
            
        return image



    def smoothimg2(self, f):
       
        
        image = np.zeros((self.Ndim, self.Ndim))

        xx = yy = np.arange(-self.Ndim/2.+0.5, self.Ndim/2., 1.)  # in original pixels

        Gx, Gy = np.meshgrid(xx, yy)

        sigma = 1. # original pixels                   
        gauss = np.exp(-((Gx**2 + Gy**2)/ ( 2.0 * sigma**2 ) ) )  
        gauss /= np.sum(gauss)
            

        for x, y, l in zip(self.X_pix, self.Y_pix, self.flux):

            # Get this star's position within the image
            
            g = f((xx-x)/self.resampling_factor, (yy-y)/self.resampling_factor) 
            
            g = convolve_fft(g, gauss)
            
            g /= np.sum(g)
            
            image += l * g
            
        return image
        
        
#     def smoothimg3(self, f):
#        
#         
#         image = np.zeros((self.Ndim, self.Ndim))
# 
#         xx = yy = np.arange(-self.Ndim/2.+0.5, self.Ndim/2., 1.)  # in original pixels
# 
#         Gx, Gy = np.meshgrid(xx, yy)
# 
#         sigma = 1. # original pixels                   
#         gauss = lambda x, y: np.exp(-((x**2 + y**2)/ ( 2.0 * sigma**2 ) ) )  
# 
#         for x, y, l in zip(self.X_pix, self.Y_pix, self.flux):
# 
#             # Get this star's position within the image
#             
#             # g = f((xx-x)/self.resampling_factor, (yy-y)/self.resampling_factor) * gauss((xx-x)/self.resampling_factor, (yy-y)/self.resampling_factor)
#             
#             g = f((xx-x)/self.resampling_factor, (yy-y)/self.resampling_factor)  * 
#             
#             g /= np.sum(g)
#             
#             image += l * g
#             
#         return image



















def observed_frame_NEW(X_arcsec, Y_arcsec, flux, filter, width=10., resampling_factor=False, pixel_scale=False, smoothed=False, PSF = None, xoffset = 0.0, yoffset = 0.0):

    img = empty()
    

    base_pixel_scale = FLARE.filters.pixel_scale[filter]

    width = width # target width in " 
    
    if resampling_factor:
        pixel_scale = base_pixel_scale / resampling_factor # the actual resolution 
        resampling_factor = resampling_factor
        
    elif pixel_scale:
        pixel_scale = pixel_scale
        resampling_factor = base_pixel_scale/pixel_scale

    else:
        pixel_scale = base_pixel_scale
        resampling_factor = 1.0
    
    Ndim = round(width / pixel_scale)
    actual_width = Ndim * pixel_scale # actual width "
    PSF = PSF # PSF object


    X_arcsec = X_arcsec
    Y_arcsec = Y_arcsec
    
    X_pix = X_arcsec/pixel_scale + xoffset # offset's are necessary so that the object doesn't in the middle of a pixel
    Y_pix = Y_arcsec/pixel_scale + yoffset # offset's are necessary so that the object doesn't in the middle of a pixel
    
    
    
    super_resolution = 5
    
    # ---- make super-resolution image     

    smoothing_parameter = 2.355
    smoothing = 'gaussian'
    sigma = smoothing_parameter/2.355
        
    if smoothing == 'gaussian':

        G = np.linspace(-(width/pixel_scale)/2., (width/pixel_scale)/2., Ndim * super_resolution) # width in final pixels

        Gx, Gy = np.meshgrid(G, G)

        sigma = self.smoothing_parameter/2.355
    
        gauss = np.exp(-((Gx**2 + Gy**2)/ ( 2.0 * sigma**2 ) ) )  
        gauss /= np.sum(gauss)
    
        img.super = np.zeros((Ndim * super_resolution,Ndim * super_resolution))
    

        for x,y,l in zip(X_pix, Y_pix, L):

            i, j = (np.abs(G - x)).argmin(), (np.abs(G - y)).argmin()

            img.super[j,i] += l
        
        img.super = convolve_fft(self.data, gauss)
        
    
    
    img.img = img.super
    
    return img   
 
 
 
 
