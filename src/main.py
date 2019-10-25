
import os
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import xarray as xr
import plot
import paths as ps
import hsa
# Define a context manager to suppress stdout and stderr.
class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in 
    Python, i.e. will suppress all print, even if the print originates in a 
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).      

    '''
    def __init__(self):
        # Open a pair of null files
        self.null_fds =  [os.open(os.devnull,os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0],1)
        os.dup2(self.null_fds[1],2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0],1)
        os.dup2(self.save_fds[1],2)
        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)

def run_hsa():

    [os.remove(os.path.join(ps.data_store,n)) for n in os.listdir(ps.data_store) if '.idx' in n]
    wx_vars = ['slp','wnd','tmp850','tmp925','pwat']
    now = datetime.now()

    for v in wx_vars:
        hsa.hsa(v)
    with open(ps.log_directory + 'timing_log.txt', "a") as f:
        f.write(f'single process total is {np.round((datetime.now() - now).total_seconds(),2)}\n')

def multi_thread():
    print('starting multi-thread')
    with open(ps.log_directory + 'current_run.txt', "r") as f:
        model_date=datetime.strptime(f.readlines()[-1][5:16],'%Y%m%d_%H')
    [os.remove(os.path.join(ps.data_store,n)) for n in os.listdir(ps.data_store) if '.idx' in n]
    print('removed idx files')
    wx_vars = ['slp','wnd','tmp850','tmp925','pwat']
    now = datetime.now()
    print('starting multiprocessing pool')
    with ProcessPoolExecutor(len(wx_vars)) as executor:
        executor.map(hsa.hsa_vectorized,wx_vars)
    for v in wx_vars:
        hsa_final = xr.load_dataset(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_{v}_hsa.nc')
        gefs_mean = xr.load_dataset(f'{ps.output_dir}{model_date.strftime("%Y%m%d_%H")}_{v}_mean.nc')
        for n in range(len(hsa_final.fhour)):
            plot.Map(hsa_final.isel(fhour=n), gefs_mean.isel(fhour=n), variable)    
    print(np.round((datetime.now() - now).total_seconds(),2))
if __name__ == "__main__":
    multi_thread()
