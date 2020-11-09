#!/usr/bin/env python

import hsa
from tqdm import tqdm
import warnings
import os
import paths as ps
warnings.filterwarnings("ignore")
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import xarray as xr
import plot
import utils
import logging


def setup_logger(name, log_file, level=logging.INFO):
    
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
summary_logger = setup_logger('summary_logger', '../logs/summary.log')
error_logger = setup_logger('error_logger', '../logs/errors.log', level=logging.ERROR)


def run_hsa():
    [os.remove(os.path.join(ps.data_store,n)) for n in os.listdir(ps.data_store) if '.idx' in n]
    wx_vars = ['slp','wnd','tmp850','tmp925','pwat']
    now = datetime.now()
    for v in wx_vars:
        hsa.hsa(v)
    with open(ps.log_directory + 'timing_log.txt', "a") as f:
        f.write(f'single process total is {np.round((datetime.now() - now).total_seconds(),2)}\n')

def multi_thread(flush=False):
    [os.remove(os.path.join(ps.data_store,n)) for n in os.listdir(ps.data_store) if '.idx' in n]
    wx_vars = ['slp','wnd','tmp850','tmp925','pwat']
    vars_flush = ((n, flush) for n in wx_vars)
    start = datetime.now()
    # likely removing, no need to identify and store model run date/time here
    # with open(ps.log_directory + 'current_run.txt', "r") as f:
    #     model_date=datetime.strptime(f.readlines()[-1][5:16],'%Y%m%d_%H')
    with ProcessPoolExecutor(len(wx_vars)) as executor:
        executor.map(hsa.hsa_vectorized,vars_flush)
    
    if flush:
        summary_logger.info(f'vectorized total time (seconds): {np.round((datetime.now() - start).total_seconds(),2)}')
    else:
        [os.remove(os.path.join(ps.data_store,n)) for n in os.listdir(ps.data_store) if '.idx' in n]
        summary_logger.info(f'uploading to itpa at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        utils.scp_call(f'{ps.log_directory}current_run.txt',f'{ps.itpa_login}:{ps.model_run_itpa_dir}')
        utils.rsync_call(ps.plot_dir, f'{ps.itpa_login}:{ps.plot_itpa_dir}')
        summary_logger.info(f'vectorized total time (seconds): {np.round((datetime.now() - start).total_seconds(),2)}, completed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        utils.cleaner()