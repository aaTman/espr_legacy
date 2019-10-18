import cartopy.crs as ccrs
import cartopy.feature as cf
import matplotlib.pyplot as plt 
import matplotlib.font_manager as fm
import paths as ps 
import numpy as np

class NorthAmerica:
    def __init__(self,**kwargs):
        self.font = fm.FontProperties(fname=ps.fpath)
        self.font_bold = fm.FontProperties(fname=ps.fpath_bold)
        if 'levels' in kwargs:
            self.levels = levels
        else:
            self.levels = np.linspace(-3,3,13)
        if 'ens_mean' in kwargs:
            self.ens_mean = ens_mean
        self.map = self._generate_map()

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
        return ax

def plot_variable(hsa, input_map):

    hsa.where(np.abs(hsa) > 0.5).plot.contourf(
        ax=input_map.map,
        transform=ccrs.PlateCarree(),
        levels=input_map.levels,
        add_colorbar=False,
        alpha=0.9
    )
    
    # if 'var_map' in args:
    #     var_map = var_map
    #     var_map.plot.contour(
    #     ax=input_map.map,
    #     transform=ccrs.PlateCarree(),
    #     levels=input_map.levels,
    #     add_colorbar=False,
    #     colors='k',
    #     alpha=0.9
    # )

    date = hsa.valid_time.dt.strftime("%Y/%m/%d %Hz").values
    step = hsa.step.values.astype("timedelta64[h]")/np.timedelta64(1, "h")
    input_map.map.set_title(f'HISTORICAL SPREAD ANOMALY',
    fontproperties=input_map.font,
    fontsize=16,
    loc='left')
    input_map.map.set_title(f'FHOUR: {step:2.0f}',
    fontproperties=input_map.font_bold,
    fontsize=14,
    loc='center')
    input_map.map.set_title(f'VALID: {date}',
    fontproperties=input_map.font_bold,
    fontsize=14,
    loc='right')
    plt.savefig('test.png',bbox_inches='tight',dpi=300)
