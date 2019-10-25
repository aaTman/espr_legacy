import cartopy.crs as ccrs
import cartopy.feature as cf
import matplotlib.pyplot as plt 
import matplotlib.font_manager as fm
import paths as ps 
import numpy as np
import xarray as xr 
from mpl_toolkits.axes_grid1 import make_axes_locatable

class Map:
    def __init__(self, hsa, input_map, variable):
        self.variable = variable
        self.hsa = self._convert_to_da(hsa)
        self.input_map = self._convert_to_da(input_map)
        self.font = fm.FontProperties(fname=ps.fpath)
        self.font_bold = fm.FontProperties(fname=ps.fpath_bold)
        self.levels = np.linspace(-3,3,13)
        self.variable_range = self._set_variable_range()
        self._generate_map()
        
    def _convert_to_da(self, array):
        if type(array) == xr.Dataset:
            array = array[[n for n in array][0]]
            return array
        else:
            return array
            
    def _set_variable_range(self):
        if self.variable == 'slp':
            return np.arange(900,1100,4)
        elif self.variable == 'pwat':
            return np.arange(0,100,2)
        elif self.variable == 'wnd':
            return np.arange(0,150,2)
        elif 'tmp' in self.variable:
            return np.arange(-50,50,4)

    def _generate_map(self):
        fig, ax = plt.subplots(figsize=(20,10), subplot_kw={'projection': ccrs.Miller()})
        ax.add_feature(cf.NaturalEarthFeature(
            'cultural', 'admin_1_states_provinces_lines', '50m',
            edgecolor='gray', facecolor='none'))
        ax.add_feature(cf.NaturalEarthFeature(
            'cultural', 'admin_1_states_provinces_lines', '50m',
            edgecolor='gray', facecolor='none'))        
        ax.add_feature(cf.LAKES, facecolor='gray')
        ax.add_feature(cf.BORDERS, edgecolor='gray')
        ax.add_feature(cf.RIVERS, edgecolor='gray')
        ax.add_feature(cf.OCEAN, facecolor='gray')
        ax.set_extent([-180,-50,20,65])
        ax.coastlines(resolution='50m')
        self.hsa = self.hsa.rename('Sigma')
        try:
            c = self.hsa.where(np.abs(self.hsa) > 0.5).plot.contourf(
                ax=ax,
                transform=ccrs.PlateCarree(),
                levels=self.levels,
                add_colorbar=True,
                cbar_kwargs={'pad':0.001, 'aspect':30},
                alpha=0.9
            )
        except ValueError:
            pass
        try:
            if self.variable == 'slp':
                cl = (self.input_map/100).plot.contour(
                    ax=ax,
                    colors = 'k',
                    transform=ccrs.PlateCarree(),
                    levels=self.variable_range,
                    add_colorbar=False,
                    linewidths=0.5)
            else:
                cl = self.input_map.plot.contour(
                ax=ax,
                colors = 'k',
                transform=ccrs.PlateCarree(),
                levels=self.variable_range,
                add_colorbar=False,
                linewidths=0.5
            )
            ax.clabel(cl, fmt='%3.0f')
        except:
            if self.variable == 'slp':
                (self.input_map/100).plot.contour(
                    ax=ax,
                    colors = 'k',
                    transform=ccrs.PlateCarree(),
                    levels=self.variable_range,
                    add_colorbar=False,
                    linewidths=0.5)
            else:
                self.input_map.plot.contour(
                ax=ax,
                colors = 'k',
                transform=ccrs.PlateCarree(),
                levels=self.variable_range,
                add_colorbar=False,
                linewidths=0.5
            )        
        date = self.hsa.valid_time.dt.strftime("%Y/%m/%d %Hz").values
        step = self.hsa.step.values.astype("timedelta64[h]")/np.timedelta64(1, "h")
        ax.set_title(f'HISTORICAL SPREAD ANOMALY',
        fontproperties=self.font,
        fontsize=16,
        loc='left')
        ax.set_title(f'FHOUR: {step:3.0f}',
        fontproperties=self.font_bold,
        fontsize=14,
        loc='center')
        ax.set_title(f'VALID: {date}',
        fontproperties=self.font_bold,
        fontsize=14,
        loc='right')
        try:
            plt.savefig(f'{ps.plot_dir}{self.variable}_{step:.0f}.png',bbox_inches='tight',dpi=150)
        except:
            pass
        plt.close('all')

# def plot_variable(hsa, input_map):

#     hsa.where(np.abs(hsa) > 0.5).plot.contourf(
#         ax=ax,
#         transform=ccrs.PlateCarree(),
#         levels=input_map.levels,
#         add_colorbar=False,
#         alpha=0.9
#     )
    
#     # if 'var_map' in args:
#     #     var_map = var_map
#     #     var_map.plot.contour(
#     #     ax=ax,
#     #     transform=ccrs.PlateCarree(),
#     #     levels=input_map.levels,
#     #     add_colorbar=False,
#     #     colors='k',
#     #     alpha=0.9
#     # )

#     date = hsa.valid_time.dt.strftime("%Y/%m/%d %Hz").values
#     step = hsa.step.values.astype("timedelta64[h]")/np.timedelta64(1, "h")
#     ax.set_title(f'HISTORICAL SPREAD ANOMALY',
#     fontproperties=input_map.font,
#     fontsize=16,
#     loc='left')
#     ax.set_title(f'FHOUR: {step:2.0f}',
#     fontproperties=input_map.font_bold,
#     fontsize=14,
#     loc='center')
#     ax.set_title(f'VALID: {date}',
#     fontproperties=input_map.font_bold,
#     fontsize=14,
#     loc='right')
#     plt.savefig('test.png',bbox_inches='tight',dpi=300)
