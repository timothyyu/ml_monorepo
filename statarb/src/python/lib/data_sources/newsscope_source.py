import os
import datetime
import pytz 
import paramiko 
import gzip

from data_source import DataSource, DataSourceError
from sftp_source import SFTPSource
import random
import string

class NewsScopeSFTPSource(SFTPSource):
    def __init__(self, host, user, password, dirsMax, compress = True):
        try:
            SFTPSource.__init__(self, host, user, password)
            self._dirsMax=int(dirsMax)
            self._compress = compress 
        except Exception, e:
            raise DataSourceError(e.__str__())

    def list_dir(self, regex):
        try:
            return SFTPSource.list(self, regex)
        except Exception, e:
            raise DataSourceError(e.__str__())

    def list(self, regex):
        cwd = self._sftp.getcwd()
        try:
            daydirs = self.list_dir(r"\d{8}")
            daydirs = sorted(daydirs, key = lambda x: x[0], reverse = True)[0:min(self._dirsMax,len(daydirs))]
            daydirs = sorted(daydirs, key = lambda x: x[0])
            
            files = []
            wd = self._sftp.getcwd()
            for daydir in daydirs:
                self.cwd(wd+"/"+daydir[0])
                for file in self.list_dir(regex):
                    files.append((daydir[0]+"/"+file[0],file[1]))
                #files.extend(self.list_dir(regex))
            files = sorted(files, key = lambda x : x[0])
            
            self.cwd(cwd)
            
            return files
        except Exception, e:
            raise DataSourceError(str(e))
        
    def copy(self, remote_path, local_path, rest=None):
        if not self._compress:
            SFTPSource.copy(self, remote_path, local_path, rest)
        else :
            tmpFileName = None
            try:
                tmpFileName = os.environ["TMP_DIR"] + "/" + "".join([random.choice(string.letters) for x in xrange(32)])
                SFTPSource.copy(self, remote_path, tmpFileName, rest)
                os.system("mkdir -p `dirname %s`" % local_path)
                f_in = open(tmpFileName, 'rb')
                f_out = gzip.open(local_path, 'wb')
                f_out.writelines(f_in)
                f_out.close()
                f_in.close()
                os.unlink(tmpFileName)
            except Exception, e:
                if os.path.isfile(tmpFileName):
                    os.unlink(tmpFileName)
                raise DataSourceError(str(e))
        
if __name__ == "__main__":
    files = source.list(r".*")
    for file in files:
        print file
