import os
import ftplib
import datetime
import pytz

import util
from data_source import DataSource, DataSourceError

class FTPSource(DataSource):
    def __init__(self, host, user, password, tz):
        try:
            self._ftp = ftplib.FTP(host, timeout=60)
            self._ftp.login(user, password)
            # 10/4/08 - suddenly passive stopped working, switching to active for now
            # 10/6/08 - back to normal
            #self._ftp.set_pasv(False)
        except ftplib.all_errors, e:
            raise DataSourceError(e.__str__())
        
        self._tzinfo = pytz.timezone(tz)
        util.info("Connected to %s" % host);

    def __del__(self):
        try:
            self._ftp.quit()
        except AttributeError:
            # Connection was never made, self._ftp doesn't exist
            pass

    def cwd(self, remote_dir):
        try:
            self._ftp.cwd(remote_dir)
        except ftplib.all_errors, e:
            raise DataSourceError(e.__str__())

    def list(self, regex):
        try:
            result = []
            self._ftp.retrlines("LIST", result.append)
            if (result[0].find("total ", 0) != -1):
                del result[0]
            return self._parse_ls(result, regex)
        except ftplib.error_perm:
            return []
        except ftplib.all_errors, e:
            raise DataSourceError(e.__str__())

    def modtime(self, path):
        try:
            result = self._ftp.sendcmd("MDTM %s" % path)
        except ftplib.error_perm:
            return None
        except ftplib.all_errors, e:
            raise DataSourceError(e.__str__())
        try:
            info = result.split(" ")[1]
            info = (info[0:4], info[4:6], info[6:8], info[8:10], info[10:12], info[12:14])
            info = [int(i) for i in info]
            # FTP's MDTM should always be UTC
            return self._tzinfo.localize(datetime.datetime(*(info[0:6]))).astimezone(pytz.utc)
        except IndexError:
            raise DataSourceError("Could not parse modtime result")

# FTP's SIZE command seems unreliable (was returning larger values)
#    def size(self, path):
#        try:
#            result = self._ftp.sendcmd("SIZE %s" % path)
#        except ftplib.all_errors, e:
#            raise DataSourceError(e.__str__())
#        try:
#            return int(result.split()[1])
#        except (ValueError, IndexError):
#            raise DataSourceError("Could not parse size result")

    def copy(self, remote_path, local_path, rest=None):
        util.info("Copying from %s to %s" % (remote_path, local_path))
        try:
            os.system("mkdir -p `dirname %s`" % local_path)
            with file(local_path, 'ab') as f:
                self._ftp.retrbinary("RETR %s" % remote_path, f.write, rest=rest)
        except ftplib.all_errors, e:
            raise DataSourceError(e.__str__())
