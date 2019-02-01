import re

class DataSourceError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class DataSource:
    def _parse_ls(self, result, regex, sizes = True):
        listing = []
        for line in result:
            if "st_size" in dir(line):
                filepath = line.filename
                filesize = line.st_size
            else:
                info = line.rstrip().split(None, 8)
                if not sizes:
                    # if we were just given a list of filenames
                    filepath = info[0]
                    filesize = None
                else:
                    # otherwise it's an actual ls output
                    filepath = info[8]
                    filesize = int(info[4])
            start = filepath.rfind('/') + 1
            if (start == -1):
                start = 0
            filename = filepath[start:]
            m = re.match(regex, filename)
            if (m != None and m.end() == len(filename)):
                listing.append((filepath, filesize))
        return listing
