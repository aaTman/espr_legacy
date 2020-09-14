#!/usr/bin/env python

from ftplib import FTP
from time import sleep
from retr import retr_files
from datetime import datetime
import paths as ps
import sys
import main
import argparse

def monitor(server, directory, temp_store, flush=False):
    log_directory = ps.log_directory
    with open(log_directory + 'current_run.txt', "r") as f:
        try:
            old_date, old_run, _ = f.readlines()[-1].split('_')
        except IndexError:
            old_date = 0
            old_run = 0
    ftp = FTP(server)
    
    ftp.login()
    ftp.cwd(directory)
    new_date = ftp.nlst("-t")[0]
    ftp.cwd(new_date)
    new_run = ftp.nlst("-t")[0]
    print(new_run)
    print(old_run)
    if new_run != old_run:
        if flush:
            new_flush_run = old_run
            new_flush_date = old_date
            ftp.cwd(f'{new_flush_run}/pgrb2ap5')
            with open(f'{log_directory}new_run.txt', "w") as f:
                f.write(new_flush_date+'_'+new_flush_run+'_\n')
            retr_files(ftp,temp_store)
            ftp.quit()
            print('flush old run starting')
            main.multi_thread(flush=flush)     
        else:  
            try:
                ftp.cwd(f'{new_run}/pgrb2ap5')
                if any('.f174' in s for s in ftp.nlst()):
                    with open(f'{log_directory}new_run.txt', "w") as f:
                        f.write(new_date+'_'+new_run+'_\n')
                    print('beginning to retrieve files at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
                    retr_files(ftp,temp_store)
                    old_date = new_date
                    old_run = new_run
                    print('completed at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    ftp.quit()
                    main.multi_thread(flush=flush)
                    with open(f'{log_directory}current_run.txt', "a") as f:
                        f.write(new_date+'_'+new_run+'_\n')
            except:         
                ftp.quit()

    else:
        ftp.quit()

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='Run listener for hsa.')
parser.add_argument("-f","-flush", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Sets flush to run or not.")
args = parser.parse_args()
monitor(ps.ftp, ps.ftp_dir, ps.data_store,args.f)
    
