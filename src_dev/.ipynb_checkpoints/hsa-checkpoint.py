import numpy as np 
import xarray as xr
import xarray.ufuncs as xu
import bottleneck
import datetime
import os
import paths as ps
import utils as ut
import plot
import subprocess
import logging

logging.basicConfig(level=logging.INFO,filename=f'{ps.log_directory}performance.log', filemode='w')

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
        self.v12 = False

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
            elif self.variable == 'slp' & self._date_string() == 'djf':
                pass
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
            elif self.variable == 'slp' and self._date_string() == 'djf':
                pass
        if self.variable == 'slp' and self._date_string() == 'djf':
            self.stat = stat
            self.v12 = True
            file = self._subset_time(0,v12=True)
            if self.fhour:
                file = file.sel(time=np.timedelta64(self.fhour,'h'))
        else:
            if self.fhour:
                file = file.sel(fhour=np.timedelta64(self.fhour,'h'))
            file = file.assign_coords(time=ut.replace_year(file.time.values, 2012))
            file = file.assign_coords({'time':file.time.values.astype('datetime64[h]')})
            file = self._subset_time(file)
            if self.fhour:   
                file = file.drop(['intTime', 'intValidTime', 'fhour'])
            else:
                file = file.drop(['intTime', 'intValidTime'])
            if self.variable == 'wnd':
                file = xu.sqrt(file[[n for n in file.data_vars][0]]**2+file[[n for n in file.data_vars][1]]**2)
        return file

    def _subset_time(self, file, v12=False):
        d64 = np.datetime64(self.date,'D')
        date_range = ut.replace_year(np.arange(d64-10,d64+11), 2012)
        if v12:
            dt2 = ut.dt2cal(date_range)
            files = os.listdir(f'{ps.rfcst_v12}slp/mean_hours')
            file_dt = [datetime.datetime.strptime(n[-18:-8],'%Y%m%d%H') for n in files]
            date_tuple_list = [(dt2[n,1],dt2[n,2]) for n in range(len(dt2))]
            file_list = [n for n in file_dt if (n.month, n.day) in date_tuple_list]
            if self.stat == 'sprd':
                v12_stat = 'std'
            else:
                v12_stat = self.stat
            files_ndjf = [n.strftime(f'../reforecast_v12/slp/{v12_stat}_hours/nh_time_pres_msl_%Y%m%d%H_{v12_stat}.nc') for n in file_list]
            file = xr.open_mfdataset(files_ndjf,
                              coords='minimal',
                              data_vars='minimal',
                              compat='override',
                              combine='nested',concat_dim='date',chunks={'date':1,'time':1})
        else:
            file = xr.concat([file.sel(time=n) for n in date_range], dim='time')
        return file

    def generate(self,stat='mean',dask=False):
        # try:
        xarr = self._retrieve_from_xr(stat, dask=dask)
        # except:
        #     raise Exception('type must be mean or sprd')
        return xarr


class NewForecastArray(object):
    def __init__(self, stat: str, variable: str, fhour: int, group: bool=False):
        self.variable = variable
        self._convert_variable()
        self.fhour = fhour
        self.stat = stat
        if self.stat in self._stat_list():
            pass
        else:
            self._convert_stat()
        if group == True:
            self._load_all()

    def _convert_variable(self):
        if self.variable in ['slp','psl','prmsl']:
            self.variable = 'prmsl'
            self.key_filter = {'typeOfLevel':'meanSea'}
        elif self.variable in ['precip','pwat']:
            self.variable = 'pwat'
            self.key_filter = {'typeOfLevel':'unknown', 'level': 0}
        elif self.variable in ['temp','tmp','tmp850','tmp925']:
            self.short_name = 't'
            if '925' in self.variable:
                self.key_filter = {'typeOfLevel':'isobaricInhPa','level': 925, 'shortName': 't'}
                self.variable = 'tmp925'
            elif '850' in self.variable:
                self.key_filter = {'typeOfLevel':'isobaricInhPa','level': 850, 'shortName': 't'}
                self.variable = 'tmp850'
            else:
                raise Exception('Temperature level must be indicated (925 or 850)')
        elif self.variable in ['wnd', 'wind', 'sfc_wind', '10m_wnd', 'u10', 'v10']:
            self.variable = 'wnd'
            self.key_filter = {'typeOfLevel': 'heightAboveGround', 'level': 10}
    
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
            subset_variable = xu.sqrt(data[[n for n in data.data_vars][0]]**2+data[[n for n in data.data_vars][1]]**2)
            subset_variable = subset_variable.drop(['heightAboveGround'])
        
        elif self.variable == 'tmp925':
            subset_variable = data['t'] - 273.15
        elif self.variable == 'tmp850':
            subset_variable = data['t'] - 273.15
        elif self.variable == 'pwat':
            subset_variable = data.drop(['level'])
        else:
            subset_variable = data
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
        try:
            new_gefs = xr.open_dataset(f'{ps.data_store}gefs_{self.stat}_{self.fhour:03}.grib2',engine='cfgrib',backend_kwargs=dict(filter_by_keys=self.key_filter,indexpath=''))
        except KeyError:
            new_gefs = xr.open_dataset(f'{ps.data_store}gefs_{self.stat}_{self.fhour:03}.grib2',engine='cfgrib',backend_kwargs=dict(filter_by_keys=self.key_filter,indexpath=''))
        subset_gefs = self._get_var(new_gefs)
        subset_gefs = self._rename_latlon(new_gefs)
        try:
            subset_gefs = self._subset_latlon(subset_gefs, subset_lat, subset_lon)
        except:
            print('error trying to subset lats and lons')
            pass
        self.date = str(subset_gefs.time.values).partition('T')[0]
        subset_gefs = self._map(subset_gefs)
        return subset_gefs

    def _load_all(self, subset_lat=None, subset_lon=None):
        try:
            new_gefs = xr.open_mfdataset(f'{ps.data_store}*{self.stat}*.grib2',
            engine='cfgrib',
            combine='nested',
            concat_dim='time',
            backend_kwargs=dict(filter_by_keys=self.key_filter,indexpath='')
            )
        except KeyError:
            import cfgrib
            new_gefs = cfgrib.open_datasets(f'{ps.data_store}gefs_mean_000.grib2')
            import pdb; pdb.set_trace()
        subset_gefs = self._get_var(new_gefs)
        subset_gefs = self._rename_latlon(new_gefs)
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
    try:
        forecast = forecast.expand_dims(dim='time')
    except ValueError:
        forecast = forecast.rename({'time':'fhour'})
        forecast = forecast.assign_coords(fhour=mclimate.fhour)
    vars = ['step','meanSea','valid_time','isobaricInhPa', 'pressure', 'heightAboveGround']
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
        new_stacked = xr.concat([mclimate, forecast[[n for n in forecast][0]]],'time')
    except ValueError:
        forecast = forecast.drop(['level'])
        new_stacked = xr.concat([mclimate[[n for n in mclimate][0]], forecast[[n for n in forecast][0]]],'time')
    
    new_stacked = new_stacked.compute()
    percentile = new_stacked.rank('time')/len(new_stacked['time'])
    return percentile

def percentile_v(mclimate, forecast, v12=False):
    
    if v12:
        forecast = forecast.rename({'time':'fhour'})
        mclimate = mclimate.rename({'time':'fhour','date':'time','latitude':'lat','longitude':'lon'})
        forecast = forecast.expand_dims(dim='time')
        fhours = [n.astype('timedelta64[m]').astype('int')/60 for n in forecast['step'].values]
        forecast['fhour'] = fhours
    else:
        try:
            forecast = forecast.expand_dims(dim='time')
        except ValueError:
            forecast = forecast.rename({'time':'fhour'})
            forecast = forecast.assign_coords(fhour=mclimate.fhour)
            forecast = forecast.expand_dims(time=[mclimate.time.values[-1]])
    vars = ['step','meanSea','valid_time','isobaricInhPa', 'pressure', 'heightAboveGround']
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
        new_stacked = xr.concat([mclimate, forecast[[n for n in forecast][0]]],'time')
    except ValueError:
        forecast = forecast.drop(['level'])
        new_stacked = xr.concat([mclimate[[n for n in mclimate][0]], forecast[[n for n in forecast][0]]],'time')
    new_stacked = new_stacked[:,::2][:,1:] # making sure the fhours align to every 6 hrs...
    percentile = xr.apply_ufunc(bottleneck.rankdata,new_stacked,kwargs={'axis':0},dask='parallelized')/len(new_stacked['time'])
    return percentile

def subset_sprd(combined_fcst_mcli, mcli_sprd):
    new_perc = combined_fcst_mcli.where(np.logical_and(combined_fcst_mcli >= combined_fcst_mcli.isel(time=-1)-0.05, combined_fcst_mcli <= combined_fcst_mcli.isel(time=-1)+0.05),drop=True)
    try:
        mcli_sprd = mcli_sprd[[n for n in mcli_sprd][0]]
    except:
        pass
    try:
        mcli_sprd = mcli_sprd.where(~np.isnan(new_perc[:-1]),drop=True)
    except ValueError:
        import pdb; pdb.set_trace()
        mcli_sprd = mcli_sprd.drop(['isobaricInhPa'])
        mcli_sprd = mcli_sprd.where(~np.isnan(new_perc[:-1]),drop=True)
    return mcli_sprd

def subset_sprd_v(percentile, mc_std, v12=False):
    mask = np.logical_and(percentile >= percentile[-1]-0.05, percentile <= percentile[-1]+0.05)[:-1]
    try:
        mc_std = mc_std[[n for n in mc_std][0]]
    except:
        pass
    if v12:
        import pdb; pdb.set_trace()
        mc_std = mc_std.rename({'time':'fhour','date':'time','latitude':'lat','longitude':'lon'})
        mc_std_t = mc_std[:,1::2]
        mask_da = xr.concat([mc_std_t[:,n][mask[:,n]] for n in range(len(mask['fhour']))])
        
        mc_std  = mc_std.where(~np.isnan(mask_da),drop=True)
    else:
        mc_std.rename({'fhour':'time','time':'fhour'})
        mask_da=xr.DataArray(mask[:-1], coords={
            'fhour':mc_std.fhour.values, 
            'time':mc_std.time.values, 
            'lat':mc_std.lat.values, 
            'lon':mc_std.lon.values 
            }, 
        dims={ 
            'time': len(mc_std.time), 
            'fhour':len(mc_std.fhour), 
            'lat': len(mc_std.lat), 
            'lon': len(mc_std.lon) 
            }
        )    
        mc_std  = mc_std.where(~np.isnan(mask_da),drop=True)

    return mc_std

def hsa_transform(gefs_sprd, subset):
    gefs_sprd = gefs_sprd.rename({'time':'fhour'})
    gefs_sprd = gefs_sprd.assign_coords(fhour=subset.fhour)
    subset_vals = (gefs_sprd - subset.mean('time'))/subset.std('time')
    subset_vals = (0.99-(-0.99))*(subset_vals-subset_vals.min(['lat','lon']))/(subset_vals.max(['lat','lon'])-subset_vals.min(['lat','lon'])) + -0.99
    subset_vals = np.arctanh(subset_vals)
    return subset_vals

def hsa(variable, hourf=168):
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
    for f in range(0,hourf+1,6):
        nfa_mean = NewForecastArray('mean', variable, f)
        gefs_mean = nfa_mean.load_forecast(subset_lat=lats,subset_lon=lons)
        nfa_sprd = NewForecastArray('sprd', variable, f)
        gefs_sprd = nfa_sprd.load_forecast(subset_lat=lats,subset_lon=lons)
        mc = MClimate(model_date, variable, f)
        mc_mu = xarr_interpolate(mc.generate(stat='mean',dask=True),gefs_mean)
        mc = MClimate(model_date, variable, f)
        mc_std = xarr_interpolate(mc.generate(stat='sprd',dask=True),gefs_mean)
        percentiles = percentile(mc_mu, gefs_mean)
        subset = subset_sprd(percentiles, mc_std)
        hsa_final = hsa_transform(gefs_sprd, subset)
        plot.Map(hsa_final, gefs_mean, variable) 
    return hsa_final

def hsa_vectorized(args,v12=False):
    variable=args[0]
    flush=args[1]
    now = datetime.datetime.now()
    lons = np.arange(180,310.1,0.5)
    lats = np.arange(20,80.1,0.5)
    with open(ps.log_directory + 'new_run.txt', "r") as f:
        model_date=datetime.datetime.strptime(f.readlines()[-1][5:16],'%Y%m%d_%H')
    if np.logical_and(os.path.isfile(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_{variable}_hsa.nc'),
    os.path.isfile(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_{variable}_mean.nc')):
        print('files previously saved')
    else:
        print(f'loading gefs {variable} forecasts')
        nfa_mean = NewForecastArray('mean',variable, None)
        gefs_mean = nfa_mean._load_all(subset_lat=lats,subset_lon=lons)
        nfa_sprd = NewForecastArray('sprd',variable, None)
        gefs_sprd = nfa_sprd._load_all(subset_lat=lats,subset_lon=lons)
        logging.info(f'loading mean/spread total time (seconds): {np.round((datetime.datetime.now() - now).total_seconds(),2)}')
        now = datetime.datetime.now()
        print(f'loaded; loading {variable} reforecasts')
        mc = MClimate(model_date, variable, None)
        mc_mu = xarr_interpolate(mc.generate(stat='mean',dask=True),gefs_mean)
        mc = MClimate(model_date, variable, None)
        mc_std = xarr_interpolate(mc.generate(stat='sprd',dask=True),gefs_mean)
        logging.info(f'mclimate + interpolate total time (seconds): {np.round((datetime.datetime.now() - now).total_seconds(),2)}')
        now = datetime.datetime.now()
        print(f'{variable} stats time')
        percentiles = percentile_v(mc_mu, gefs_mean, v12=v12)
        logging.info(f'percentile total time (seconds): {np.round((datetime.datetime.now() - now).total_seconds(),2)}')
        now = datetime.datetime.now()
        subset = subset_sprd_v(percentiles, mc_std, v12=v12)
        logging.info(f'subset total time (seconds): {np.round((datetime.datetime.now() - now).total_seconds(),2)}')
        now = datetime.datetime.now()
        hsa_final = hsa_transform(gefs_sprd, subset)
        logging.info(f'hsa total time (seconds): {np.round((datetime.datetime.now() - now).total_seconds(),2)}')
        now = datetime.datetime.now()
        gefs_mean = gefs_mean.rename({'time':'fhour'})
        print(f'saving {variable} files...')
        try:
            os.mkdir(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}')
        except FileExistsError:
            print('path already created')
        if flush:
            os.mkdir(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_flush')
            percentiles.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_flush/{variable}_percentiles.nc',mode='w')
            subset.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_flush/{variable}_subset.nc',mode='w')
            hsa_final.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_flush/{variable}_hsa.nc',mode='w')
            gefs_mean.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_flush/{variable}_mean.nc',mode='w')
        else:
            hsa_final.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}/{variable}_hsa.nc',mode='w')
            gefs_mean.to_netcdf(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}/{variable}_mean.nc',mode='w')
    if flush:
        pass
    else:
        print('starting plots')
        for n in range(len(hsa_final.fhour)):
            plot.Map(hsa_final.isel(fhour=n), gefs_mean.isel(fhour=n), variable, model_date,dpi=72)   
        print('finished plots')
