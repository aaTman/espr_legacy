from ftplib import FTP
from time import sleep
from retr import retr_files
from datetime import datetime
import paths as ps
import sys

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
        print('logged into ftp at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        try:
            print('new: {}, old: {} '.format(new_run, old_run) + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        except ValueError:
            print('new: {}, old: not yet created '.format(new_run) + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ftp.cwd(new_run+'/pgrb2ap5')
        if any('.f168' in s for s in ftp.nlst()):
            print('beginning to retrieve files at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')) 
            retr_files(ftp,temp_store)
            old_date = new_date
            old_run = new_run
            with open(log_directory + 'current_run.txt', "a") as f:
                f.write(new_date+'_'+new_run+'_\n')
            print('completed at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ftp.quit()
    else:
        ftp.quit()

monitor(ps.ftp, ps.ftp_dir, ps.data_store)
    