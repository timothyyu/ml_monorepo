import os
import datetime
import pytz

from data_sources.data_source import DataSource, DataSourceError

class FileSource(DataSource):
    def __init__(self, remote_dir = None):
        if (remote_dir is not None):
            self.cwd(remote_dir)

    def cwd(self, remote_dir):
        self._remote_dir = remote_dir
        if (not os.path.isdir(remote_dir)):
            raise DataSourceError("Source directory does not exist")

    def list(self, regex):
        try:
            result = os.popen("ls -l %s 2>/dev/null" % (self._remote_dir)).readlines()
        except AttributeError:
            # If self._remote_dir is not set return an empty result
            return []
        if (result[0].find("total ", 0) != -1):
            del result[0]
        return self._parse_ls(result, regex)

    def list_recursive(self, regex, newer = None, sizes = True):
        if newer is not None:
            newer_str = " -newer %s" % newer
        else:
            newer_str = ""
        if sizes:
            sizes_str = " -exec ls -l {} \;"
        else:
            sizes_str = ""
        result = os.popen("find %s -type f" % self._remote_dir + newer_str + sizes_str + " | sort 2>/dev/null").readlines()
        return self._parse_ls(result, regex, sizes)

    def modtime(self, path):
        try:
            result = os.popen("stat -c %Y " + "%s/%s" % (self._remote_dir, path)).readlines()[0]
            # stat %Y is always UTC
            return datetime.datetime.fromtimestamp(int(result), pytz.timezone("UTC"))
        except IndexError:
            return None

# FTP's SIZE wasn't reliable so we're using the output from ls
#    def size(self, path):
#        try:
#            result = os.popen("stat -c %s " + "%s/%s" % (self._remote_dir, path)).readlines()[0]
#            return int(result)
#        except (ValueError, IndexError):
#            raise DataSourceError("Could not get size of file")

    def copy(self, remote_path, local_path, rest=None):
        os.system("mkdir -p `dirname %s`" % local_path)
        result = os.system("cp %s/%s %s" % (self._remote_dir, remote_path, local_path))
        if (result != 0):
            raise DataSourceError("Could not copy file")
