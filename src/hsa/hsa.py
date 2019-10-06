import numpy as np 
import xarray as xr 
import pygrib as pg 
from bisect import bisect
from scipy.stats import percentileofscore
from datetime import datetime, timedelta
import ..utils.paths as ps
import ..utils.utils as ut
from datetime import date

class MClimate(object):
    """
    Model climatology object.

    This class instantiates metadata for an MClimate xarray 
    object that can be poroduced with MClimate.generate()
    date: string or datetime.date object.
    variable: string
    fhour: int
    percentile: int or float
    """
    def __init__(self, date, variable, fhour, percentile=10):
        self.date = date(date)
        self.variable = variable
        if self.variable in self._var_list():
            pass
        else:
            self.variable = self._convert_variable()
        self.fhour = fhour
        self.percentile = percentile

    def _var_list(self):
        return ['slp','pwat','tmp925','tmp850','wnd']
    
    def _convert_variable(self):
        if 'slp' or 'psl' in self.variable:
            self.variable = 'slp'
        if 'pwat' or 'precip' in self.variable:
            self.variable = 'pwat'
        
    def _date_string(self):
        djf = [1,2,12]
        mam = [3,4,5]
        jja = [6,7,8]
        son = [9,10,11]
        if self.date.month in djf:
            return 'djf'
        if self.date.month in mam:
            return 'mam' 
        if self.date.month in jja:
            return 'jja' 
        if self.date.month in son:
            return 'son'  

    def _retrieve_from_xr(self, stat):
        file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}')
        file = file.assign_coords(fhour=file.fhour.values.astype('timedelta64[h]'))
        file = file.assign_coords(time=t.time.values.astype('datetime64[h]'))
        file = file.assign_coords(time=ut.replace_year(file.time.values, 2012))
        file = file.sel(fhour=np.timedelta64(self.fhour,'h'))
        file = self._subset_time(file)
        file = file.drop(['intTime','intValidTime'])
        return file

    def _subset_time(self, file):
        d64 = np.datetime64(self.date)
        date_range = ut.replace_year(np.arange(d64-10,d64+11), 2012)
        file = xr.concat([t.sel(time=n) for n in date_range_year], dim='time')

    def generate(self,type='mean'):
        if type == 'mean':
            xarr = _retrieve_from_xr('mean')
        elif type == 'sprd':
            xarr = _retrieve_from_xr('sprd')
        else:
            raise Exception('type must be mean or sprd')
        return xarr

def xarr_interpolate(original,new):
    




    
