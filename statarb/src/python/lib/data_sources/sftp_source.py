import os
import datetime
import pytz 
import paramiko 
import binascii

from data_source import DataSource, DataSourceError

class SFTPSource(DataSource):
    def __init__(self, host, user, password):
        try:
            self._transport = paramiko.Transport((host, 22))
            
            if password is not None:
                self._transport.connect(username=user, password=password)
            else:
                agent = paramiko.Agent()
                agent_keys = agent.get_keys()
                if len(agent_keys) == 0:
                    raise DataSourceError("Error performing passwordless login")
                
                success = False
                for key in agent_keys:
                    try:
                        self._transport.connect(username=user, pkey=key)
                        success = True
                        break
                    except paramiko.SSHException:
                        pass
                
                if not success:
                    raise DataSourceError("Error performing passwordless login")
                                
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        except Exception, e:
            raise DataSourceError(e.__str__())

    def __del__(self):
        try:
            self._sftp.close()
            self._transport.close()
        except AttributeError:
            # Connection was never made, self._ftp doesn't exist
            pass

    def cwd(self, remote_dir):
        try:
            self._sftp.chdir(remote_dir)
        except Exception, e:
            raise DataSourceError(e.__str__())

    def list(self, regex):
        try:
            result = self._sftp.listdir_attr()
            return self._parse_ls(result, regex)
        except Exception, e:
            raise DataSourceError(e.__str__())

    def modtime(self, path):
        try:
            result = self._sftp.stat(path).st_mtime
        except Exception, e:
            raise DataSourceError(e.__str__())
        try:
            return datetime.datetime.utcfromtimestamp(result).replace(tzinfo=pytz.utc)
        except:
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
        assert rest == None, "SFTP doesn't support partial downloads"
        try:
            os.system("mkdir -p `dirname %s`" % local_path)
            self._sftp.get(remote_path, local_path)
        except Exception, e:
            raise DataSourceError(e.__str__())

    def put(self, local_path, remote_path):
        try:
            self._sftp.put(local_path, remote_path)
        except Exception, e:
            raise DataSourceError(e.__str__())
