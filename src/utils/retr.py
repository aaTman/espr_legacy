from ftplib import FTP 
import numpy as np
from datetime import datetime

def retr_files(ftp, temp_store):
    log_directory = '/home/taylorm/espr/logs/'
    file_list = ftp.nlst()
    file_valid_list = [n for n in file_list if np.logical_and('geavg' in n, '.idx' not in n)]
    file_valid_list = [n for n in file_valid_list if np.logical_and(int(n[-3:]) <= 168, int(n[-3:]) % 6 == 0)]
    for n in file_valid_list:
        fname = 'gefs_'+n[-3:]+'.grib2'
        try:
            ftp.retrbinary("RETR " + n, open(temp_store + fname, 'wb').write)
        except:
            f = open(log_directory + 'retrieval_log.txt', "a+")
            f.write(file_valid_list + ' failure at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'\n')
            f.close()
            break
    f = open(log_directory + 'retrieval_log.txt', "a+")
    f.write('completed at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'\n')
    f.close()

         