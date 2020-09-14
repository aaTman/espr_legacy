import numpy as np
import os 
from datetime import datetime, timedelta 
import paths as ps 
import subprocess
import shutil

def replace_year(x, year):
    """ Year must be a leap year for this to work """
    # Add number of days x is from JAN-01 to year-01-01 
    x_year = np.datetime64(str(year)+'-01-01') +  (x - x.astype('M8[Y]'))

    # Due to leap years calculate offset of 1 day for those days in non-leap year
    yr_mn = x.astype('M8[Y]') + np.timedelta64(59,'D')
    leap_day_offset = (yr_mn.astype('M8[M]') - yr_mn.astype('M8[Y]') - 1).astype(np.int)

    # However, due to days in non-leap years prior March-01, 
    # correct for previous step by removing an extra day
    non_leap_yr_beforeMarch1 = (x.astype('M8[D]') - x.astype('M8[Y]')).astype(np.int) < 59
    non_leap_yr_beforeMarch1 = np.logical_and(non_leap_yr_beforeMarch1, leap_day_offset).astype(np.int)
    day_offset = np.datetime64('1970') - (leap_day_offset - non_leap_yr_beforeMarch1).astype('M8[D]')

    # Finally, apply the day offset 
    x_year = x_year - day_offset
    return x_year

def cleaner():

    # for file_name in os.listdir(ps.output_dir):
    #     if (datetime.now() - datetime.strptime(file_name[0:11],'%Y%m%d_%H')).total_seconds() > 604800:
    #         os.remove(f'{ps.output_dir}{file_name}')
    for file_name in os.listdir(ps.plot_dir):
        if (datetime.now() - datetime.strptime(file_name[0:11],'%Y%m%d_%H')).total_seconds() > 604800:
           shutil.rmtree(f'{ps.plot_dir}{file_name}')

def scp_call(source, dest):
    subprocess.call(['scp','-r',source,dest],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def rsync_call(source, dest):
    subprocess.call(['rsync','-avh','--delete-before',source,dest],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        