
def preferUSAndLowerIssueId(database,rows,timestamp):
    
    def __compareIssueIds(id1,id2):
        if len(id1)==len(id2):
            if id1<=id2:
                return -1
            else:
                return 1
        else:
            if len(id1)<len(id2):
                return -1
            else:
                return 1
    
    best="999999999"
    secid=0
    for row in rows:
        issueid=database.getCsidFromSecid(row["secid"],timestamp)[1]
        if __compareIssueIds(issueid, best)<0:
            best=issueid
            secid=row["secid"]
    return secid

def preferUS(database,rows,timestamp):
    
    us=[]
    for row in rows:
        coid,issueid=database.getCsidFromSecid(row["secid"],timestamp)
        if issueid is not None and len(issueid)==2:
            us.append(row)
    
    if len(us)==1:
        return us[0]["secid"]
    else:
        return None

def noneOnAmbiguity(database,rows,timestamp):
    return None
        
    
