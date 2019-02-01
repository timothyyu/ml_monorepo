import dateutil.parser

def read_info_file(filepath):
    lines = file(filepath + ".info").readlines()
    info = dict()
    info["date_last_absent"] = lines[0].replace('\n', '')
    if (info['date_last_absent'] == ""):
        info['date_last_absent'] = None
    else:
        info['date_last_absent'] = dateutil.parser.parse(info['date_last_absent'])
    info["date_first_present"] = dateutil.parser.parse(lines[1].replace('\n', ''))
    info["date_modified"] = dateutil.parser.parse(lines[2].replace('\n', ''))
    info["size"] = lines[3].replace('\n', '')
    info["md5sum"] = lines[4].replace('\n', '')

    return info

def load_tickers(filename):
    tic2sec = dict()
    sec2tic = dict()
    for row in open(filename):
        fields = row.split("|")
        sec = int(fields[1])
        ticker = fields[0]
        sec2tic[sec] = ticker
        if ticker not in tic2sec:
            tic2sec[ticker] = sec
        else:
            raise Exception("Duplicate ticker %s" % ticker)
        if '.' in ticker:
            ticker2 = ticker.replace('.', '')
            if ticker2 not in tic2sec:
                tic2sec[ticker2] = sec
            else:
                raise Exception("Duplicate ticker %s" % ticker)
    return tic2sec, sec2tic
