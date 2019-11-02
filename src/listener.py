#!/usr/bin/env python

from ftplib import FTP
from time import sleep
from retr import retr_files
from datetime import datetime
import paths as ps
import sys
import main

def monitor(server, directory, temp_store):
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

    if new_run != old_run:
        ftp.cwd(new_run+'/pgrb2ap5')
        if any('.f174' in s for s in ftp.nlst()):
            with open(log_directory + 'new_run.txt', "w") as f:
                f.write(new_date+'_'+new_run+'_\n')
            print('beginning to retrieve files at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
            retr_files(ftp,temp_store)
            old_date = new_date
            old_run = new_run
            print('completed at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ftp.quit()
            # main.run_hsa()
            main.multi_thread()
            with open(log_directory + 'current_run.txt', "a") as f:
                f.write(new_date+'_'+new_run+'_\n')
    else:
        ftp.quit()

monitor(ps.ftp, ps.ftp_dir, ps.data_store)
    
