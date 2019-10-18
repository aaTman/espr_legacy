import numpy as np 
import xarray as xr
import xarray.ufuncs as xu
from bisect import bisect
from scipy.stats import percentileofscore
import paths as ps
import utils as ut
import datetime
import cfgrib
from dask.diagnostics import ProgressBar
import plot

class MClimate(object):
    """
    Model climatology object.

    This class instantiates metadata for an MClimate xarray 
    object that can be produced with MClimate.generate()

    Parameters
    ---------
    date : string or datetime.date
        The date of the model run. Hour is not relevant as the 
        reforecast is only run once daily.
    variable : string
        The variable of interest. Can be slp, pwat, tmp925, tmp850,
        or wnd (surface) currently. Other short names will be 
        accepted for the most part.
    fhour : int
        Forecast hour of the model run; each MClimate object will
        be unique to each forecast hour.
    percentage : int or float
        The percentage of the MClimate distribution to subset at 
        each point, e.g. 10 will take 5% of MClimate values below 
        and above the model run's value.
        
    """
    def __init__(self, model_date, variable, fhour, percentage=10):
        if isinstance(model_date, datetime.date) or isinstance(model_date, datetime.datetime):
            self.date = model_date
        else:
            try:
                self.date = datetime.datetime.strptime(model_date,'%Y-%m-%d')
            except:
                raise Exception('Please enter date as yyyy-mm-dd')
        self.variable = variable
        if self.variable in self._var_list():
            pass
        else:
            self._convert_variable()
        self.fhour = fhour
        self.percentage = percentage

    def _var_list(self):
        return ['slp','pwat','tmp925','tmp850','wnd']
    
    def _convert_variable(self):
        if 'slp' or 'psl' in self.variable:
            self.variable = 'slp'
        elif 'precip' in self.variable:
            self.variable = 'pwat'
        elif 'temp' or 'tmp' in self.variable:
            if '925' in self.variable:
                self.variable = 'tmp925'
            elif '850' in self.variable:
                self.variable = 'tmp850'
            else:
                raise Exception('Temperature level must be indicated (925 or 850)')
        elif 'wind' in self.variable:
            self.variable = 'wnd'
        
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

    def _retrieve_from_xr(self, stat, dask=False):
        if dask == False:  
            if self.variable == 'wnd':
                file = xr.open_mfdataset(f'{ps.rfcst}/*{self.variable}_{stat}_{self._date_string()}.nc',combine='by_coords')  
            elif self.variable == 'tmp925':
                self.variable = 'tmp'
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc')
                file = file.sel(pressure=925)
                file = file.drop(['pressure'])
            elif self.variable == 'tmp850':
                self.variable = 'tmp'
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc')
                file = file.sel(pressure=850)
                file = file.drop(['pressure'])
                print(file)
            else:
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc')

        else:
            if self.variable == 'wnd':
                file = xr.open_mfdataset(f'{ps.rfcst}/*{self.variable}_{stat}_{self._date_string()}.nc',combine='by_coords', chunks={'time': 10})  
            elif self.variable == 'tmp925':
                self.variable = 'tmp'
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc')
                file = file.sel(pressure=925)
            elif self.variable == 'tmp850':
                self.variable = 'tmp'
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc')
                file = file.sel(pressure=850)
            else:
                file = xr.open_dataset(f'{ps.rfcst}/{self.variable}_{stat}_{self._date_string()}.nc', chunks={'time': 10})
        file = file.sel(fhour=np.timedelta64(self.fhour,'h'))
        file = file.assign_coords(time=ut.replace_year(file.time.values, 2012))
        file = file.assign_coords({'time':file.time.values.astype('datetime64[h]')})
        file = self._subset_time(file)   
        file = file.drop(['intTime', 'intValidTime', 'fhour'])
        if self.variable == 'wnd':
            file = xu.sqrt(file[[n for n in file.data_vars][0]]**2+file[[n for n in file.data_vars][1]]**2)
        return file

    def _subset_time(self, file):
        d64 = np.datetime64(self.date,'D')
        date_range = ut.replace_year(np.arange(d64-10,d64+11), 2012)
        file = xr.concat([file.sel(time=n) for n in date_range], dim='time')
        return file

    def generate(self,type='mean',dask=False):
        try:
            xarr = self._retrieve_from_xr(type, dask=dask)
        except:
            raise Exception('type must be mean or sprd')
        return xarr


class NewForecastArray(object):
    def __init__(self, stat: str, variable: str, fhour: int):
        self.variable = variable
        if self.variable in self._var_list():
            pass
        else:
            self._convert_variable()
        self.fhour = fhour
        self.stat = stat
        if self.variable in self._stat_list():
            pass
        else:
            self._convert_stat()
    def _convert_variable(self):
        if self.variable in ['slp','psl']:
            self.variable = 'prmsl'
        elif 'precip' in self.variable:
            self.variable = 'pwat'
        elif self.variable in ['temp','tmp']:
            if '925' in self.variable:
                self.variable = 'tmp925'
            elif '850' in self.variable:
                self.variable = 'tmp850'
            else:
                raise Exception('Temperature level must be indicated (925 or 850)')
        elif 'wind' in self.variable:
            self.variable = 'wnd'
    
    def _convert_stat(self):
        if self.stat in {'avg','mu'}:
            self.stat = 'mean'
        elif self.stat in {'std', 'sigma', 'spread'}:
            self.stat = 'sprd'
    
    def _var_list(self):
        return ['prmsl','pwat','tmp','wnd']

    def _map(self, data):
        if self.variable == 'prmsl':
            data = data.rename({'prmsl':'Pressure'})
        elif self.variable == 'pwat':
            data = data.rename({'pwat':'Precipitable_water'})
        return data

    def _stat_list(self):
        return ['sprd', 'mean']
    
    def _get_var(self, data):
        if self.variable == 'wnd':
            subset_variable = [n for n in data if 'v10' in n][0]
            subset_variable = xu.sqrt(subset_variable[[n for n in subset_variable.data_vars][0]]**2+subset_variable[[n for n in subset_variable.data_vars][1]]**2)
            subset_variable = subset_variable.drop(['heightAboveGround'])

        elif self.variable == 'tmp925':
            subset_variable = [n for n in data if 't' in n][0]['t'].sel(isobaricInhPa=925) + 273.15
        elif self.variable == 'tmp850':
            subset_variable = [n for n in data if 't' in n][0]['t'].sel(isobaricInhPa=850) + 273.15
        else:
            subset_variable = [m for m in data if self.variable in m][0]
        return subset_variable
        
    def _subset_latlon(self, data, lats, lons):
        data = data.where(np.logical_and(data.lon>=np.min(lons), data.lon<=np.max(lons)), drop=True)
        data = data.where(np.logical_and(data.lat>=np.min(lats), data.lat<=np.max(lats)), drop=True)
        return data
        
    def _rename_latlon(self, forecast):
        try:
            forecast = forecast.rename_dims({'latitude':'lat','longitude':'lon'}).rename_vars({'latitude':'lat','longitude':'lon'})
        except AttributeError:
            forecast = forecast.rename({'latitude':'lat','longitude':'lon'})
        return forecast
  
    def load_forecast(self, subset_lat=None, subset_lon=None):
        new_gefs = cfgrib.open_datasets(f'{ps.data_store}gefs_{self.stat}_{self.fhour:03}.grib2')
        subset_gefs = self._get_var(new_gefs)
        subset_gefs = self._rename_latlon(subset_gefs)
        try:
            subset_gefs = self._subset_latlon(subset_gefs, subset_lat, subset_lon)
        except:
            print('error trying to subset lats and lons')
            pass
        self.date = str(subset_gefs.time.values).partition('T')[0]
        subset_gefs = self._map(subset_gefs)
        return subset_gefs
        
def xarr_interpolate(original, new, on='latlon'):
    if on == 'latlon':
        new_lat = [i for i in new.coords if 'lat' in i][0]
        new_lon = [i for i in new.coords if 'lon' in i][0]
        old_lat = [i for i in original.coords if 'lat' in i][0]
        old_lon = [i for i in original.coords if 'lon' in i][0]
        original_i = original.interp({old_lat : new[new_lat].values}).interp({old_lon : new[new_lon].values})
        return original_i
    else:
        raise Exception('latlon interpolation only works as of now...')

def percentile(mclimate, forecast):
    forecast = forecast.expand_dims(dim='time')
    vars = ['step','meanSea','valid_time','isobaricInhPa', 'pressure']
    for var in vars:
        try:
            forecast = forecast.drop([var])
        except ValueError:
            pass
    try:
        mclimate = mclimate.drop(['pressure'])
    except ValueError:
        pass
    try:
        new_stacked = xr.concat([mclimate[[n for n in mclimate][0]], forecast[[n for n in forecast][0]]],'time')
    except TypeError:
        new_stacked = xr.concat([mclimate[[n for n in mclimate][0]], forecast],'time')

    new_stacked = new_stacked.compute()
    percentile = new_stacked.rank('time')/len(new_stacked['time'])
    return percentile

def subset_sprd(combined_fcst_mcli, mcli_sprd):
    new_perc = combined_fcst_mcli.where(np.logical_and(combined_fcst_mcli >= combined_fcst_mcli.isel(time=-1)-0.05, combined_fcst_mcli <= combined_fcst_mcli.isel(time=-1)+0.05),drop=True)
    try:
        mcli_sprd = mcli_sprd[[n for n in mcli_sprd][0]]
    except:
        pass
    mcli_sprd = mcli_sprd.where(~np.isnan(new_perc[:-1]),drop=True)
    return mcli_sprd

def hsa_transform(gefs_sprd, subset):
    subset_vals = (gefs_sprd - subset.mean('time'))/subset.std('time')
    subset_vals = (0.99-(-0.99))*(subset_vals-subset_vals.min())/(subset_vals.max()-subset_vals.min()) + -0.99
    subset_vals = np.arctanh(subset_vals)
    return subset_vals

def hsa(variable):
    with open(ps.log_directory + 'current_run.txt', "r") as f:
        model_date=datetime.datetime.strptime(f.readlines()[-1][5:13],'%Y%m%d')
    lons = np.arange(180,310.1,0.5)
    lats = np.arange(20,80.1,0.5)
    if variable == 'slp':
        var_vals = np.linspace(900, 1100,4)
    elif variable in ['tmp850','tmp925']:
        var_vals = np.linspace(-40, 40, 4)
    elif variable == 'wnd':
        var_vals = np.linspace(-100,100, 4)
    na = plot.NorthAmerica(ens_mean=var_vals)
    for f in range(0,169,6):
        nfa_mean = NewForecastArray('mean', variable, f)
        gefs_mean = nfa_mean.load_forecast(subset_lat=lats,subset_lon=lons)
        nfa_sprd = NewForecastArray('sprd', variable, f)
        gefs_sprd = nfa_sprd.load_forecast(subset_lat=lats,subset_lon=lons)
        mc = MClimate(model_date, variable, f, percentage=10)
        mc_mu = xarr_interpolate(mc.generate(type='mean',dask=True),gefs_mean)
        mc_std = xarr_interpolate(mc.generate(type='sprd',dask=True),gefs_mean)
        percentiles = percentile(mc_mu, gefs)
        subset = subset_sprd(percentiles, mc_std)
        hsa_final = hsa_transform(gefs_sprd, subset)
        plot.plot_variable(hsa_final, variable, gefs_mean)
    return hsa_final
