import zipfile
import datafiles
import datetime
import xml.sax.handler
import xml.sax.xmlreader
import util
import newdb
import xdrlib
import os

database = newdb.get_db()

def _date(date):
    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")

def _datePlusOne(date, delta=datetime.timedelta(days=1)):
    return _date(date) + delta

def _appendEndDateToMonth(date):
    if date[4:6] in ("01", "03", "05", "07", "08", "10", "12"):
        return date + "31"
    elif date[4:6] in ("04", "06", "09", "11"):
        return date + "30"
    else:
        return date + "28"

def _consecutiveEqual(list, start, key):
    end = start
    while end < len(list) and key(list[start]) == key(list[end]):
        end = end + 1
    return start, end

class ActualsHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        self.state = {}
        self.mult = {"U":1.0, "T":1e3, "M":1e6, "B":1e9, "P":1.0, "MC":0.01}
        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source 
        self.batch = []
        
    #When recording current position, only the elements that are
    #involved in the characters function need to be tracked
    def startElement(self, name, attributes):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = attributes["code"]
        elif name == "fYPeriod":
            self.position[name]=True
            self.state["periodType"] = attributes["periodType"]
            self.state["endDate"] = _appendEndDateToMonth(attributes["fPeriodEnd"])
        elif name == "fYActual":
            self.position[name]=True
            self.state["actual"] = attributes["type"]
            self.state["unit"] = attributes["unit"]
        elif name == "actValue":
            self.position[name] = True
            self.state["value"] = ""
            self.state["annDate"] = attributes["announcementDate"]
            self.state["upDate"] = attributes["updated"]
            self.state["currency"] = attributes.get("currCode", "NA")
            
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "fYPeriod":
            #pass
            self.position[name]=False
        elif name == "fYActual":
            self.position[name]=False
            self.__process()
        elif name == "actValue":
            self.position[name] = False
    
    def characters(self, data):
        if self.position.get("actValue", False):
            self.state["value"] += data
        elif self.position.get("coId", False):
            self.state["coid"] += data
            
    def endDocument(self):
        #print "Processing company: {}".format(self.state["coid"])
        self.__batchProcess()
        #print datetime.datetime.now(),self.state["coid"]
    
    def __process(self):
        
        event = self.state["event"]
        actualName = self.state["actual"] + "_" + self.state["periodType"]
        date = int(self.state["endDate"])
        annDate = util.convert_date_to_millis(_date(self.state["annDate"]))
        timestamp = self.timestamp if self.backfill == 0 else annDate
            
        self.batch.append((event, actualName, date, timestamp, self.state["value"], self.state["unit"], self.state["currency"], annDate, self.state["periodType"]))
        
    #process data as a batch, sort by timestamp and then insert. Some reuters history files contained data out-of-chronological-order
    def __batchProcess(self):
#        if self.coId is not None and self.coId<0: #previously failed to identify mapping:
#            return
#        elif self.coId==None:
#            row=database.getCompanyMapping("reuters", self.state["coid"])
#            if row is None:
#                util.warning("Unmappable company {}".format(self.state["coid"]))
#                self.coId=-1
#                return
#            else:
#                self.coId=row["compustat"]
        rkd = int(self.state["coid"])
        annDates = {}
        self.batch.sort(key=lambda x: x[3])
        for event, actualName, date, timestamp, value, unit, currency, annDate, periodType in self.batch:
            annDates[(date, periodType, timestamp)] = annDate
            
            if event in ("Refresh", "New", "Historical-Update"): #insert
                value = float(value) * self.mult[unit]
                database.insertCoActual(rkd, self.source, actualName, "n", date, value, currency, timestamp, None, self.backfill)
            elif event in ("Historical-Delete"):
                database.deleteCoActual(rkd, self.source, actualName, "n", date, timestamp)
            else:
                util.error("Unsupported command in ActualsHandler: {}".event)
                raise Exception
            
        for k, v in sorted(annDates.iteritems(), key=lambda x:x[0][2]):
            date = k[0]
            periodType = k[1]
            timestamp = k[2]
            annDate = v

            database.insertCoActual(rkd, self.source, "ANN_DATE", "d", date, annDate, "NA", timestamp, None, self.backfill)
            database.insertCoActual(rkd, self.source, "ANN_DATE_" + periodType, "d", date, annDate, "NA", timestamp, None, self.backfill)
            
class BrokerHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        
        self.id = None
        self.name = ""
        self.start = None
        self.event = None

        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
    def startElement(self, name, attributes):
        if name == "event":
            self.position[name]=True
            self.event = attributes["code"]
        elif name == "broker":
            self.position[name]=True
            self.id = attributes["brokerId"]
            self.start = attributes["start"]
            self.name = ""
        elif name == "brokerName":
            self.position[name] = True
            
    def endElement(self, name):
        if name == "event":
            #pass
            self.position[name]=False
        elif name == "broker":
            self.position[name]=False
            self.__process()
        elif name == "brokerName":
            self.position[name] = False
    
    def characters(self, data):
        if self.position.get("brokerName", False):
            self.name = self.name + data
            
    def endDocument(self):
        pass
    
    def __process(self):        
        if self.event in ("Refresh", "New", "Revise", "Historical-Update", "Historical-Insert"): #insert
            database.insertBroker(self.source, self.id, self.name, util.convert_date_to_millis(_date(self.start)))
        else:
            util.error("Unsupported command in BrokerHandler: {}".event)
            raise Exception
                        
    
class CompanyHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source, filepath, verifyOnly):
        self.position = {}
        
        self.coInfo = {}
        self.issues = {}
        self.currentIssue = None
        self.issueXrefType = None
        self.statusType = None
        self.taxonomies = {}
        self.currentTaxonomy = None
        self.currentcurrency = None
        
        self.backfill = backfill
        self.timestamp = timestamp
        self.source = source
        self.verifyOnly = verifyOnly
        self.filepath = filepath
        
        self.coidInconcistencies = []
        self.secidInconsistencies = []
        
        self.coInfo["primary"] = None
        self.coInfo["relationship"] = None
                
    def startElement(self, name, attributes):
        if name == "RepNo":
            self.position[name] = True
            self.coInfo["repno"] = ""
        elif name == "CompanyXref" and attributes["Type"] == "FProXRef":
            self.position[name] = True
            self.coInfo["fproxref"] = ""
        elif name == "CompanyName":
            self.position[name] = True
            self.coInfo["name"] = ""
        elif name == "CompanyStatus":
            self.position[name] = True
            self.coInfo["active"] = ""
        elif name == "Status":
            self.position[name] = True
            self.statusType = attributes["Type"]
        elif name == "RelatedCompanies":
            self.position[name] = True
        elif name == "Company" and self.position.get("RelatedCompanies", False):
            self.position[name]=True
            if "Primary" in attributes:
                self.coInfo["primary"] = attributes["RepNo"]    
            if "Relationship" in attributes:
                self.coInfo["relationship"] = attributes["Relationship"]
        elif name == "Issue":
            self.position[name] = True
            self.currentIssue = attributes["ID"]
            self.issues[self.currentIssue] = dict()
            self.issues[self.currentIssue]["type"] = attributes["Type"]
            self.issues[self.currentIssue]["order"] = attributes["Order"]
        elif name == "IssueXref":
            self.position[name] = True
            self.issueXrefType = attributes["Type"]
            self.issues[self.currentIssue][self.issueXrefType] = ""
        elif name == "IssueStatus":
            self.position[name] = True
            self.issues[self.currentIssue]["active"] = ""
            self.issues[self.currentIssue]["public"] = ""
        elif name == "Exchange":
            self.position[name] = True
            self.issues[self.currentIssue]["exchange"] = attributes["Code"]
            self.issues[self.currentIssue]["country"] = attributes.get("Country", "NA") #Default to NA which matches our null for country
            self.issues[self.currentIssue]["region"] = attributes.get("Region","NONE") #We can do the same here because NA is a region! (North america)
        elif name == "ListingType":
            self.position[name] = True
            self.issues[self.currentIssue]["sharesperlisting"] = attributes.get("SharesPerListing", 1)
            self.issues[self.currentIssue]["listingtype"] = ""
        elif name == "Taxonomy":
            self.position[name] = True
            self.currentTaxonomy = attributes["Type"]
        elif name == "Detail" and self.position.get("Taxonomy", False) and attributes.get("Order", "0") == "1":
            self.position[name] = True
            self.taxonomies[self.currentTaxonomy] = attributes["Code"]
        elif name == "Currencies":
            self.position[name] = True
            self.coInfo["primary_currency"] = ""
            self.coInfo["statement_currency"] = ""
        elif name == "Currency":
            self.position[name] = True
            self.currentcurrency = attributes["Type"]
            
    def endElement(self, name):
        if name == "CompanyXref":
            self.position[name] = False
        elif name == "RepNo":
            self.position[name] = False
        elif name == "CompanyName":
            self.position[name] = False
        elif name == "CompanyStatus":
            self.position[name] = False
        elif name == "Status":
            self.position[name] = False
        elif name == "Company":
            self.position[name] = False
        elif name == "RelatedCompanies":
            self.position[name] = False
        elif name == "Issue":
            self.position[name] = False
        elif name == "IssueXref":
            self.position[name] = False
        elif name == "IssueStatus":
            self.position[name] = False
        elif name == "Exchange":
            self.position[name] = False
        elif name == "Taxonomy":
            self.position[name] = False
        elif name == "Detail" and self.position.get("Taxonomy", False):
            self.position[name] = False
        elif name == "ListingType":
            self.position[name] = False
        elif name == "Currencies":
            self.position[name] = False
        elif name == "Currency":
            self.position[name] = False
    
    def characters(self, data):
        if self.position.get("CompanyXref", False):
            self.coInfo["fproxref"] += data
        elif self.position.get("RepNo", False):
            self.coInfo["repno"] += data
        elif self.position.get("CompanyStatus", False) and self.position.get("Status", False) and self.statusType == "ActiveStatus":
            self.coInfo["active"] += data
        elif self.position.get("IssueXref", False):
            self.issues[self.currentIssue][self.issueXrefType] += data
        elif self.position.get("IssueStatus", False) and self.position.get("Status", False) and self.statusType == "ActiveStatus":
            self.issues[self.currentIssue]["active"] += data
        elif self.position.get("IssueStatus", False) and self.position.get("Status", False) and self.statusType == "PublicStatus":
            self.issues[self.currentIssue]["public"] += data
        elif self.position.get("CompanyName", False):
            self.coInfo["name"] += data
        elif self.position.get("ListingType", False):
            self.issues[self.currentIssue]["listingtype"] += data
        elif self.position.get("Currency", False) and self.currentcurrency == "FinancialStatements":
            self.coInfo["statement_currency"] += data
        elif self.position.get("Currency", False) and self.currentcurrency == "PrimaryIssuePrice":
            self.coInfo["primary_currency"] += data
            
    def endDocument(self):
        self.__map3()
#        if self.verifyOnly:
#            self.__verifyMappings()
#        else:
#            ok=self.__establishCompanyMapping()
#            if ok:
#                self.__updateXrefs()
#                self.__updateAttributes()
                
    def __map1(self):
        row = database.getTimelineRow(database.REUTERS_REF, {"rkd":int(self.coInfo["fproxref"])}, self.timestamp)
        oldCoid = row["csid"] if row is not None else None

        if len(self.issues) == 0:
            coid = None
        else:
            #only use the primary issue: Frist type=C, order=1 and if not existent type=P order=1
            issues = sorted(self.issues.itervalues(), key=lambda x: x["order"] + x["type"])
            issue = issues[0]
            
            secids = []
            if issue.get("exchange", "NA") is not "NA" and issue.get("country", None) in ("USA", "CAN"): #use cusip
                if "CUSIP" in issue:
                    secid = database.getSecidFromXref("CUSIP", issue["CUSIP"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
            elif issue.get("exchange", "NA") is not "NA" and "country" in issue:
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                if "ISIN" in issue:
                    secid = database.getSecidFromXref("ISIN", issue["ISIN"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
            
            #all secids must agree
            secids.sort()
            if len(secids) == 0 or secids[0] != secids[-1]:
                coid = None
            else:
                coid, issueid = database.getCsidFromSecid(secid)
                            
        if oldCoid is None and coid is None:
            pass
        elif oldCoid is None and coid is not None:
            database.killOrDeleteTimelineRow(database.REUTERS_REF, {"coid":coid}, self.timestamp)
            database.insertTimelineRow(database.REUTERS_REF, {"rkd":self.coInfo["fproxref"]}, {"coid":coid}, self.timestamp)
        elif oldCoid is not None and oldCoid == coid:
            pass
        elif oldCoid is not None and coid is not None and oldCoid != coid:
            database.killOrDeleteTimelineRow(database.REUTERS_REF, {"coid":coid}, self.timestamp)
            database.insertTimelineRow(database.REUTERS_REF, {"rkd":self.coInfo["fproxref"]}, {"coid":coid}, self.timestamp)
        else:
            database.killOrDeleteTimelineRow(database.REUTERS_REF, {"rkd":self.coInfo["fproxref"]}, self.timestamp)

    def __map2(self):
        for id, issue in self.issues.iteritems():
            #add dummy xref
            issue["RKD"] = self.coInfo["fproxref"] + "." + id
            
            for xref in ("CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"): 
                if xref in issue: database.insertTimelineRow(database.REUTERS + "xref", {"rkd":issue["RKD"], "xref_type":database.getXrefType(xref)}, {"value":issue[xref]}, self.timestamp)
                else: database.killOrDeleteTimelineRow(database.REUTERS + "xref", {"rkd":issue["RKD"], "xref_type":database.getXrefType(xref)}, self.timestamp)
            
            oldSecid = database.getSecidFromXref("RKD", self.coInfo["fproxref"] + "." + id, self.timestamp, self.source, newdb.xrefsolve.noneOnAmbiguity)
            
            secids = []
            if issue.get("exchange", "NA") is not "NA" and issue.get("country", None) in ("USA", "CAN"): #use cusip
                if "CUSIP" in issue:
                    secid = database.getSecidFromXref("CUSIP", issue["CUSIP"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
#                if "SEDOL" in issue:
#                    secid=database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_idhist",newdb.xrefsolve.preferUSAndLowerIssueId)
#                    if secid is not None: secids.append(secid)
            elif issue.get("exchange", "NA") is not "NA" and "country" in issue:
#                if "SEDOL" in issue:
#                    secid=database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_g_idhist",newdb.xrefsolve.noneOnAmbiguity)
#                    if secid is not None: secids.append(secid)
                if "ISIN" in issue:
                    secid = database.getSecidFromXref("ISIN", issue["ISIN"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    
            #all secids must agree
            secids.sort()
            if len(secids) == 0 or secids[0] != secids[-1]:
                secid = None
                    
            if oldSecid is None and secid is None:
                pass
            elif oldSecid is None and secid is not None:
                for xref in ("RKD", "CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"):
                    if xref in issue: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"value":issue[xref], "source":database.getSourceType(self.source), "xref_type":database.getXrefType(xref)}, self.timestamp)
                    if xref in issue: database.insertTimelineRow(database.XREF_TABLE, {"secid":secid, "xref_type":database.getXrefType(xref), "source":database.getSourceType(self.source)}, {"value":issue[xref]}, self.timestamp)
                    #else: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":secid,"source":database.getSourceType(self.source),"xref_type":database.getXrefType(xref)}, self.timestamp)
            elif oldSecid is not None and oldSecid == secid:
                for xref in ("RKD", "CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"):
                    #if xref in issue: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":secid,"source":database.getSourceType(database.getSourceType(self.source)),"xref_type":database.getXrefType(xref)}, self.timestamp)
                    if xref in issue: database.insertTimelineRow(database.XREF_TABLE, {"secid":secid, "xref_type":database.getXrefType(xref), "source":database.getSourceType(self.source)}, {"value":issue[xref]}, self.timestamp)
                    else: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":secid, "source":database.getSourceType(self.source), "xref_type":database.getXrefType(xref)}, self.timestamp)
            elif oldSecid is not None and secid is not None and oldSecid != secid:
                for xref in ("RKD", "CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"):
                    if xref in issue: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"value":issue[xref], "source":database.getSourceType(self.source), "xref_type":database.getXrefType(xref)}, self.timestamp)
                    if xref in issue: database.insertTimelineRow(database.XREF_TABLE, {"secid":secid, "xref_type":database.getXrefType(xref), "source":database.getSourceType(self.source)}, {"value":issue[xref]}, self.timestamp)
                    else: database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":secid, "source":database.getSourceType(self.source), "xref_type":database.getXrefType(xref)}, self.timestamp)
            else:
                for xref in ("RKD", "CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"):
                    database.killOrDeleteTimelineRow(database.XREF_TABLE, {"secid":oldSecid, "source":database.getSourceType(self.source), "xref_type":database.getXrefType(xref)}, self.timestamp)
    
    def __insertAttribute(self, rkd, issueid, attributeType, attributeName, attributeValue, born):
        assert isinstance(rkd, int)
        assert isinstance(issueid, int)
        assert attributeType in ("s", "n", "x")
        assert isinstance(born, long)
        
        type=None
        if attributeType == "n":
            value = float(attributeValue)
            datatype = "n";
            table = database.REUTERS + "n"
            type=database.getAttributeType(attributeName, self.source, datatype, table)
            updates=database.insertTimelineRow(table, {"rkd":rkd, "issueid":issueid, "type":type}, {"value":value}, born, None, util.dict_fields_eq_num_stable)
        elif attributeType == "s":
            value = str(attributeValue)
            value = value[0:database.MAX_STR_LEN]
            datatype = "s"
            table = database.REUTERS + "s"
            type=database.getAttributeType(attributeName, self.source, datatype, table)
            updates=database.insertTimelineRow(table, {"rkd":rkd, "issueid":issueid, "type":type}, {"value":value}, born)
        elif attributeType == "x":
            table = database.REUTERS + "xref"
            value = attributeValue
            type=database.getAttributeType(attributeName,self.source,"s",table)
            updates=database.insertTimelineRow(table, {"rkd":rkd, "issueid":issueid, "xref_type":database.getXrefType(attributeName)}, {"value":value}, born)
        
        if type is not None : database.updateAttributeStats(type, *updates)
        
    def __deleteAttribute(self, rkd, issueid, attributeType, attributeName, born):
        assert isinstance(rkd, int)
        assert isinstance(issueid, int)
        assert attributeType in ("s", "n", "x")
        assert isinstance(born, long)

        type=None
        if attributeType == "n":
            datatype = "n";
            table = database.REUTERS + "n"
            type=database.getAttributeType(attributeName, self.source, datatype, table)
            updates=database.killOrDeleteTimelineRow(table, {"rkd":rkd, "issueid":issueid, "type":type}, born)
        elif attributeType == "s":
            datatype = "s";
            table = database.REUTERS + "s"
            type=database.getAttributeType(attributeName, self.source, datatype, table)
            updates=database.killOrDeleteTimelineRow(table, {"rkd":rkd, "issueid":issueid, "type":type}, born)
        elif attributeType == "x":
            table = database.REUTERS + "xref"
            type=database.getAttributeType(attributeName, self.source, "s", table)
            updates=database.killOrDeleteTimelineRow(table, {"rkd":rkd, "issueid":issueid, "xref_type":database.getXrefType(attributeName)}, born)
            
        if type is not None : database.updateAttributeStats(type, *updates)
            
    def __map3(self):
        rkd = int(self.coInfo["fproxref"])
        self.__insertAttribute(rkd, 0, "s", "REPNO", self.coInfo["repno"], self.timestamp)
        self.__insertAttribute(rkd, 0, "n", "CO_ACTIVE", self.coInfo["active"], self.timestamp)
        self.__insertAttribute(rkd, 0, "s", "CO_NAME", util.printableString(self.coInfo["name"]), self.timestamp)
        self.__insertAttribute(rkd, 0, "s", "STATEMENT_CURRENCY", self.coInfo["statement_currency"], self.timestamp)
        self.__insertAttribute(rkd, 0, "s", "PRIMARY_ISSUE_CURRENCY", self.coInfo["primary_currency"], self.timestamp)
        if self.coInfo["primary"] is not None: self.__insertAttribute(rkd, 0, "s", "PRIMARY" , self.coInfo["primary"], self.timestamp)
        else: self.__deleteAttribute(rkd, 0, "s", "PRIMARY", self.timestamp)
        if self.coInfo["relationship"] is not None: self.__insertAttribute(rkd, 0, "n", "RELATIONSHIP" , self.coInfo["relationship"], self.timestamp)
        else: self.__deleteAttribute(rkd, 0, "n", "RELATIONSHIP", self.timestamp)
        for taxonomy in ("RBSS2004", "NAICS1997", "SIC1987", "MGSECTOR", "MGINDUSTRY"):
            if taxonomy in self.taxonomies: self.__insertAttribute(rkd, 0, "s", taxonomy, self.taxonomies[taxonomy], self.timestamp)
            else: self.__deleteAttribute(rkd, 0, "s", taxonomy, self.timestamp)
        
        for id, issue in sorted(self.issues.iteritems()):
            if "Ticker" in issue: issue["TIC"]=issue["Ticker"]
            for xref in ("TIC","CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"): 
                if xref in issue: self.__insertAttribute(rkd, int(id), "x" , xref, issue[xref], self.timestamp)
                else: self.__deleteAttribute(rkd, int(id), "x" , xref, self.timestamp)
            
            self.__insertAttribute(rkd, int(id), "s", "ISSUE_TYPE", issue["type"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "n", "ISSUE_ORDER", issue["order"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "n", "ISSUE_ACTIVE", issue["active"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "n", "ISSUE_PUBLIC", issue["public"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "s", "EXCHANGE", issue["exchange"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "s", "COUNTRY", issue["country"], self.timestamp)
            self.__insertAttribute(rkd, int(id), "s", "REGION", issue["region"], self.timestamp)
            if "listingtype" in issue: self.__insertAttribute(rkd, int(id), "s", "LISTING_TYPE", issue["listingtype"], self.timestamp)
            else: self.__deleteAttribute(rkd, int(id), "s", "LISTING_TYPE", self.timestamp)
            if "sharesperlisting" in issue: self.__insertAttribute(rkd, int(id), "n", "SHARES_PER_LISTING", issue["sharesperlisting"], self.timestamp)
            else: self.__deleteAttribute(rkd, int(id), "n", "SHARES_PER_LISTING", self.timestamp)
            
    def __establishCompanyMapping(self):
        row = database.getCompanyMapping("reuters", self.coInfo["fproxref"])
        oldCoid = row["compustat"] if row is not None else None

        note = ["RKD {} {}".format(self.coInfo["fproxref"], oldCoid)]
        #try to establish a mapping through compustat_idhist
        if len(self.issues) == 0:
            coid = None
            note.append("No issues")
        else:
            #only use the primary issue: Frist type=C, order=1 and if not existent type=P order=1
            issues = sorted(self.issues.itervalues(), key=lambda x: x["order"] + x["type"])
            issue = issues[0]
            
            secids = []
            if issue.get("exchange", "NA") is not "NA" and issue.get("country", None) in ("USA", "CAN"): #use cusip
                if "CUSIP" in issue:
                    secid = database.getSecidFromXref("CUSIP", issue["CUSIP"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    note.append("CUSIP {} {} {}".format(issue["CUSIP"], secid, database.getCsidFromSecid(secid)[0] if secid is not None else None))
                else:
                    note.append("CUSIP {} {} {}".format(None, None, None))   
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    note.append("SEDOL {} {} {}".format(issue["SEDOL"], secid, database.getCsidFromSecid(secid)[0] if secid is not None else None))
                else:
                    note.append("SEDOL {} {} {}".format(None, None, None))
            elif issue.get("exchange", "NA") is not "NA" and "country" in issue:
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    note.append("SEDOL {} {} {}".format(issue["SEDOL"], secid, database.getCsidFromSecid(secid)[0] if secid is not None else None))
                else:
                    note.append("SEDOL {} {} {}".format(None, None, None))
                if "ISIN" in issue:
                    secid = database.getSecidFromXref("ISIN", issue["ISIN"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    note.append("ISIN {} {} {}".format(issue["ISIN"], secid, database.getCsidFromSecid(secid)[0] if secid is not None else None))
                else:   
                    note.append("ISIN {} {} {}".format(None, None, None))
            
            coids = []
            for secid in secids:
                coid, issueid = database.getCsidFromSecid(secid)
                assert coid is not None
                coids.append(coid)
                
            #all secids must agree
            coids.sort()
            if len(coids) == 0:
                util.warning("Failed to map active={} company {}. No coids found".format(self.coInfo["active"], self.coInfo["fproxref"]))
                coid = None
            elif coids[0] != coids[-1]:
                util.warning("Failed to map active={} company {}. Disagreeing coids".format(self.coInfo["active"], self.coInfo["fproxref"]))
                coid = None
            else:
                coid = coids[0]
            
        if oldCoid is None and coid is None:
            return False
        elif oldCoid is None and coid is not None:
            #successfully established new mapping
            database.createCompanyMapping("compustat", coid, "reuters", self.coInfo["fproxref"], True)
            return True
        elif oldCoid is not None and oldCoid == coid:
            return True
        elif oldCoid is not None and oldCoid != coid:
            #erturn the existing mapping but report the anomaly
            util.warning("Inconsistent mapping: {}".format(",".join(note)))
            database.insertMappingFailure(util.now(), self.source, self.filepath, self.coInfo["fproxref"], oldCoid, coid, ",".join(note))
            return True
        
    def __updateXrefs(self):
        for id, issue in self.issues.iteritems():
            oldSecid = database.getSecidFromXref("RKD", self.coInfo["fproxref"] + "." + id, self.timestamp, self.source, newdb.xrefsolve.noneOnAmbiguity)
            
            #if secid is None: #try to establish secid
            note = ["RKD {} {}".format(self.coInfo["fproxref"] + "." + id, oldSecid)]
            secids = []
            if issue.get("exchange", "NA") is not "NA" and issue.get("country", None) in ("USA", "CAN"): #use cusip
                if "CUSIP" in issue:
                    secid = database.getSecidFromXref("CUSIP", issue["CUSIP"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    note.append("CUSIP {} {}".format(issue["CUSIP"], secid))
                else:
                    note.append("CUSIP {} {}".format(None, None))
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    note.append("SEDOL {} {}".format(issue["SEDOL"], secid))
                else:
                    note.append("SEDOL {} {}".format(None, None))
            elif issue.get("exchange", "NA") is not "NA" and "country" in issue:
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    note.append("SEDOL {} {}".format(issue["SEDOL"], secid))
                else:
                    note.append("SEDOL {} {}".format(None, None))
                if "ISIN" in issue:
                    secid = database.getSecidFromXref("ISIN", issue["ISIN"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    note.append("ISIN {} {}".format(issue["ISIN"], secid))
                else:
                    note.append("ISIN {} {}".format(None, None))
                    
            if len(secids) < 2 or secids[0] != secids[1]:
                #util.warning("No mappings achieved for {}.{}".format(self.coInfo["fproxref"],id))
                secid = None
                #continue
            else:
                secid = secids[0]
                #database.insertXref(secid, self.source, "RKD", self.coInfo["fproxref"]+"."+id, self.timestamp)
                
            if oldSecid is None and secid is None:
                util.warning("No mappings achieved for {}.{}".format(self.coInfo["fproxref"], id))
                continue
            elif oldSecid is None and secid is not None:
                database.insertXref(secid, self.source, "RKD", self.coInfo["fproxref"] + "." + id, self.timestamp)
            elif oldSecid is not None and oldSecid == secid:
                pass
            elif oldSecid is not None and oldSecid != secid:
                util.warning("Insonsistent mapping: {}".format(",".join(note)))
                database.insertMappingFailure(util.now(), self.source, self.filepath, self.coInfo["fproxref"] + "." + id, oldSecid, secid, ",".join(note))
                secid = oldSecid
            
            #proceed with using the oldSecid
            assert secid is not None
            for xref in ("CUSIP", "ISIN", "SEDOL", "RIC", "DisplayRIC"):
                if xref in issue:
                    database.insertXref(secid, self.source, xref, issue[xref], self.timestamp)
                    
    def __updateAttributes(self):
        row = database.getCompanyMapping("reuters", self.coInfo["fproxref"])
        if row is None:
            return
        
        coid = row["compustat"]
        for attributeName, attributeValue in self.taxonomies.iteritems():
            database.insertAttribute("co", "n", coid, 0L, self.source, attributeName, attributeValue, self.timestamp, None, 0)
            
    def __verifyMappings(self):        
        #verify compustat<->reuters company mapping
        row = database.getCompanyMapping("reuters", self.coInfo["fproxref"])
        if row is None:
            return
        
        oldCoid = row["compustat"]
        
        #try to establish a mapping through compustat_idhist
        #only use the primary issue: Frist type=C, order=1 and if not existent type=P order=1
        if len(self.issues) == 0:
            self.coidInconcistencies.append({"RKD":(self.coInfo["fproxref"], oldCoid)})
            return
        
        #find the primary issue
        issues = sorted(self.issues.itervalues(), key=lambda x: x["order"] + x["type"])
        primaryIssue = issues[0]
            
        for id, issue in self.issues.iteritems():
            oldSecid = database.getSecidFromXref("RKD", self.coInfo["fproxref"] + "." + id, self.timestamp, self.source, newdb.xrefsolve.noneOnAmbiguity)
            
            if oldSecid is None:
                continue
            
            #Potential Secid Inconsistency
            psi = {}
            psi["RKD"] = (self.coInfo["fproxref"] + "." + id, oldSecid)
            
            pci = {} #potential coid inconcistency
            pci["RKD"] = (self.coInfo["fproxref"], oldCoid)
            
            secids = []
            if issue.get("exchange", "NA") is not "NA" and issue.get("country", None) in ("USA", "CAN"): #use cusip
                if "CUSIP" in issue:
                    secid = database.getSecidFromXref("CUSIP", issue["CUSIP"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    psi["CUSIP"] = (issue["CUSIP"], secid)
                    pci["CUSIP"] = (issue["CUSIP"], None if secid is None else database.getCsidFromSecid(secid)[0])
                else:
                    psi["CUSIP"] = (None, None)
                    pci["CUSIP"] = (None, None)
                    
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_idhist", newdb.xrefsolve.preferUSAndLowerIssueId)
                    if secid is not None: secids.append(secid)
                    psi["SEDOL"] = (issue["SEDOL"], secid)
                    pci["SEDOL"] = (issue["SEDOL"], None if secid is None else database.getCsidFromSecid(secid)[0])
                else:
                    psi["SEDOL"] = (None, None)
                    pci["SEDOL"] = (None, None)
                    
            elif issue.get("exchange", "NA") is not "NA" and "country" in issue:
                if "SEDOL" in issue:
                    secid = database.getSecidFromXref("SEDOL", issue["SEDOL"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    psi["SEDOL"] = (issue["SEDOL"], secid)
                    pci["SEDOL"] = (issue["SEDOL"], None if secid is None else database.getCsidFromSecid(secid)[0])
                else:
                    psi["SEDOL"] = (None, None)
                    pci["SEDOL"] = (None, None)
                    
                if "ISIN" in issue:
                    secid = database.getSecidFromXref("ISIN", issue["ISIN"], self.timestamp, "compustat_g_idhist", newdb.xrefsolve.noneOnAmbiguity)
                    if secid is not None: secids.append(secid)
                    psi["ISIN"] = (issue["ISIN"], secid)
                    pci["ISIN"] = (issue["ISIN"], None if secid is None else database.getCsidFromSecid(secid)[0])
                else:
                    psi["ISIN"] = (None, None)
                    pci["ISIN"] = (None, None)
                        
            if len(secids) < 2 or secids[0] != secids[1]:
                secid = None
            else:
                secid = secids[0]
            
            #established inconcistency at the secid level. check the inconcistency at the company level.
            if oldSecid != secid:
                self.secidInconsistencies.append(psi)
                
            if primaryIssue == issue:                                
                coids = []
                for secid in secids:
                    coid, issueid = database.getCsidFromSecid(secid)
                    assert coid is not None
                    coids.append(coid)
                
                #all secids must agree
                coids.sort()
                if len(coids) == 0:
                    self.coidInconcistencies.append(pci)
                elif coids[0] != coids[-1]:
                    self.coidInconcistencies.append(pci)
                
class PeriodModelHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        self.state = {}
        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
    def startElement(self, name, attributes):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = attributes["code"]
        elif name == "fYPeriodSeries":
            self.position[name]=True
            self.state["start"] = attributes["startDate"]
        elif name == "fYPeriodSequence":
            self.position[name]=True
            self.state["seqno"] = attributes["seqNo"]
        elif name == "fYPeriod":
            self.position[name]=True
            self.state["periodType"] = attributes["periodType"]
            self.state["periodEndDate"] = _appendEndDateToMonth(attributes["fPeriodEnd"])
            self.state["periodNum"] = attributes.get("periodNum",0)
            self.state["pAdvanceDate"] = attributes.get("pAdvanceDate",None)
            self.state["expectDate"] = attributes.get("expectDate",None)
            self.state["dateStatus"] = attributes.get("dateStatus",None)
            self.state["marketPhase"] = attributes.get("marketPhase", None)
            
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "fYPeriodSeries":
            #pass
            self.position[name]=False
        elif name == "fYPeriodSequence":
            #pass
            self.position[name]=False
        elif name == "fYPeriod":
            self.position[name]=False
            self.__process()

    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
            
    def endDocument(self):
        pass
        #print self.state["coid"]
    
    def __process(self):                
        rkd = int(self.state["coid"])   
        event = self.state["event"]
        offset = int(self.state["seqno"])
        seq = int(self.state["periodNum"])
        perioddate=int(self.state["periodEndDate"])
        announced = 1 if self.state["pAdvanceDate"] is not None else 0
        advdate = self.state["pAdvanceDate"] if announced == 1 else self.state["expectDate"]
        advdate = util.convert_date_to_millis(_date(advdate)) if advdate is not None else None
        datestatus = self.state["dateStatus"]
        phase = int(self.state["marketPhase"]) if self.state["marketPhase"] is not None else None
        attName = "PERIOD_"+self.state["periodType"]
        timestamp = self.timestamp if self.backfill==0 else util.convert_date_to_millis(_date(self.state["start"]))
        table=database.REUTERS+"period"
        #dummy create attribute if needed
        attType=database.getAttributeType(attName, self.source, "d", table)
        
        if event in ("Refresh"): #insert
            updates=database.insertTimelineRow(table, {"rkd" : rkd, "type" : attType, "offset" : offset, "seq" : seq}, {"perioddate" : perioddate, "advdate" : advdate, "announced" : announced, "backfill" : self.backfill, "status" : datestatus, "phase" : phase} , timestamp)
            database.updateAttributeStats(attType,*updates)
        else:
            util.error("Unsupported command in ActualsHandler: {}".event)
            raise Exception

class DetailedEstimatesHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.processCalls = 0;
        self.position = {}
        self.state = {}
        self.mult = {"U":1.0, "T":1e3, "M":1e6, "B":1e9, "P":1.0, "MC":0.01}
        
        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
        self.batch = []
        
    def startElement(self, name, att):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = att["code"]
        elif name == "broker":
            self.position[name]=True
            self.state["broker"] = att["brokerId"]
        elif name == "fYPeriod":
            self.position[name]=True
            self.state["periodType"] = att["periodType"]
            self.state["endDate"] = _appendEndDateToMonth(att["fPeriodEnd"])
        elif name == "fYEstimate":
            self.position[name]=True
            self.state["estimate"] = att["type"]
            self.state["unit"] = att["unit"]
            self.state["estimateType"] = "period"
        elif name == "nPEstimate":
            self.position[name]=True
            self.state["estimate"] = att["type"]
            self.state["unit"] = att["unit"]
            self.state["estimateType"] = "point"
        elif name == "detEstimate":
            self.position[name]=True
            self.state["confirmations"] = []
            self.state["suppressions"] = []
        elif name == "estValue":
            self.position[name]=True
            self.state["orig"] = att["orig"]
            self.state["expir"] = att.get("expir", None)
        elif name == "value":
            self.position[name] = True
            self.state["value"] = ""
            self.state["currency"] = att.get("currCode", "NA")
        elif name == "confirmationDate":
            self.position[name] = True
            self.state["confDate"] = ""
        elif name == "suppressFlag":
            self.position[name]=True
            self.state["suppressions"].append((att["orig"], att.get("expir", None)))
            
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "broker":
            #pass
            self.position[name]=False
        elif name == "fYPeriod":
            #pass
            self.position[name]=False
        elif name == "fYEstimate":
            #pass
            self.position[name]=False
        elif name == "nPEstimate":
            #pass
            self.position[name]=False
        elif name == "detEstimate":
            #pass
            self.position[name]=False
            self.__process()
        elif name == "estValue":
            #pass
            self.position[name]=False
        elif name == "value":
            self.position[name] = False
        elif name == "confirmationDate":
            self.position[name] = False
            self.state["confirmations"].append(self.state["confDate"])
        elif name == "suppressFlag":
            #pass
            self.position[name]=False
            

    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
        elif self.position.get("value", False):
            self.state["value"] += data
        elif self.position.get("confirmationDate", False):
            self.state["confDate"] += data
            
    def endDocument(self):
        pass
        #print self.state["coid"],self.processCalls
            
    def __process(self):
#        if self.coId is not None and self.coId<0: #previously failed to identify mapping:
#            return
#        elif self.coId==None:
#            row=database.getCompanyMapping("reuters", self.state["coid"])
#            if row is None:
#                util.warning("Unmappable company {}".format(self.state["coid"]))
#                self.coId=-1
#                return
#            else:
#                self.coId=row["compustat"]
        
        self.processCalls = self.processCalls + 1

        rkd = int(self.state["coid"])
        broker = self.state["broker"]
        if self.state["estimateType"] == "period":
            date = int(self.state["endDate"])
            estimateName = self.state["estimate"] + "_" + self.state["periodType"] + "_DE"
        else:
            date = 0L
            estimateName = self.state["estimate"] + "_DE"
        orig = util.convert_date_to_millis(_date(self.state["orig"]))
        expir = None if self.state["expir"] is None else util.convert_date_to_millis(_date(self.state["expir"]))
        event = self.state["event"]
        
        if event in ("Refresh", "New", "Revise", "Historical-Insert", "Historical-Update"):
            #get data
            value = float(self.state["value"]) * self.mult[self.state["unit"]]
            currency = self.state["currency"]
                        
            timestamp = self.timestamp if self.backfill == 0 else orig
            
            if event == "Revise": #do it first to protect ourselves from stupid reuters, in case it inserts and revises something in the sam e file
                oldOrig = _getMostRecentLiveOrig(rkd, self.source, estimateName, broker, date, "n")
                if oldOrig is not None:
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, oldOrig, orig, 'T', timestamp, None, self.backfill)
            elif event == "Historical-Update":
                database.deleteCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
                        
            #insert start
            database.insertCoEstimate(rkd, self.source, estimateName, "n", broker, date, orig, value, currency, timestamp, None, self.backfill)
            #database.insertCoEstimateFlags(self.coId, self.source, estimateName, "n", broker, date, orig, orig, 'C', timestamp, None, self.backfill)
                        
            #insert confirmations
            for confirmDate in self.state["confirmations"]:    
                confirmDate = util.convert_date_to_millis(_date(confirmDate))
                timestamp = self.timestamp if self.backfill == 0 else confirmDate
                if confirmDate != orig: #optimization
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, confirmDate, 'C', timestamp, None, self.backfill)
                
            #insert suppressions, will probably overwrite some insertions
            for suppressRange in self.state["suppressions"]:
                suppressStart = util.convert_date_to_millis(_date(suppressRange[0]))
                suppressEnd = None if suppressRange[1] is None else util.convert_date_to_millis(_date(suppressRange[1]))
                
                timestamp = self.timestamp if self.backfill == 0 else suppressStart
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressStart, 'S', timestamp, None, self.backfill)
                
                if suppressEnd is not None:
                    timestamp = self.timestamp if self.backfill == 0 else suppressEnd
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressEnd, 'U', timestamp, None, self.backfill)
                                                    
            #insert end, probably to be overwritten by the next record. we assume that historical refresh detEstimate records are given in 
            #chronological (orig) order
            if expir is not None:
                timestamp = self.timestamp if self.backfill == 0 else expir
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
        elif event in ("Confirm"):            
            #assert that there is a single confirmation
            assert len(self.state["confirmations"]) == 1
            
            confirmDate = self.state["confirmations"][-1]    
            confirmDate = util.convert_date_to_millis(_date(confirmDate))
            timestamp = self.timestamp if self.backfill == 0 else confirmDate
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, confirmDate, 'C', timestamp, None, self.backfill)
        elif event in ("Stop"):            
            timestamp = self.timestamp if self.backfill == 0 else expir
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
        elif event in ("Suppress"):            
            #assert that there is a single suppression
            assert len(self.state["suppressions"]) == 1
            
            suppressDate = self.state["suppressions"][-1][0]
            suppressDate = util.convert_date_to_millis(_date(suppressDate))
            timestamp = self.timestamp if self.backfill == 0 else suppressDate
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressDate, 'S', timestamp, None, self.backfill)
        elif event in ("Unsuppress"):
            #assert that there is a single suppression
            assert len(self.state["suppressions"]) == 1
            
            unsuppressDate = self.state["suppressions"][-1][1]
            unsuppressDate = util.convert_date_to_millis(_date(unsuppressDate))
            timestamp = self.timestamp if self.backfill == 0 else unsuppressDate
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, unsuppressDate, 'U', timestamp, None, self.backfill)
        elif event in ("Historical-Delete"):
            #delete start
            timestamp = self.timestamp if self.backfill == 0 else orig
            database.deleteCoEstimate(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
            database.deleteCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
        else:
            util.error("Unknown command in DetailedEstimatesHandler: {}".format(event))
            raise Exception

class ConsensusEstimatesHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.processCalls = 0
        self.position = {}
        self.state = {}
        self.mult = {"U":1.0, "T":1e3, "M":1e6, "B":1e9, "P":1.0, "MC":0.01, "N":1}
        self.statistics = {}
        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
        self.batch1 = []
        self.batch2 = []
        
    def startElement(self, name, att):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = att["code"]
        elif name == "fYPeriod":
            self.position[name]=True
            self.state["periodType"] = att["periodType"]
            self.state["endDate"] = _appendEndDateToMonth(att["fPeriodEnd"])
        elif name == "fYEstimate":
            self.position[name]=True
            self.state["estimate"] = att["type"]
            self.state["unit"] = att["unit"]
            self.state["estimateType"] = "period"
        elif name == "nPEstimate":
            self.position[name]=True
            self.state["estimate"] = att["type"]
            self.state["unit"] = att["unit"]
            self.state["estimateType"] = "point"
        elif name == "consEstimate":
            self.position[name]=True
            self.state["statistic"] = att["type"]
            #if "unit" in att: self.state["unit"]=att["unit"]
            self.state["orig"] = att["orig"]
            self.state["expir"] = att.get("expir", None)
        elif name == "consValue":
            self.position[name] = True
            self.state["value"] = ""
            self.state["currency"] = att.get("currCode", "NA")
   
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "fYPeriod":
            #pass
            self.position[name]=False
        elif name == "fYEstimate":
            self.position[name]=False
            self.__process()
            self.statistics.clear()
        elif name == "nPEstimate":
            self.position[name]=False
            self.__process()
            self.statistics.clear()
        elif name == "consEstimate":
            #pass
            self.position[name]=False
            #self.__process()
        elif name == "consValue":
            self.position[name] = False
            try:
                group = self.statistics[self.state["orig"]]
            except KeyError:
                group = {}
                self.statistics[self.state["orig"]] = group
            finally:
                group[self.state["statistic"]] = (self.state["value"], self.state["currency"], self.state["expir"])

    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
        elif self.position.get("consValue", False):
            self.state["value"] += data
                            
    def endDocument(self):
        pass
        #print datetime.datetime.now(),self.state["coid"],self.processCalls
        
    def __process(self):        
#        if self.coId is not None and self.coId<0: #previously failed to identify mapping:
#            return
#        elif self.coId==None:
#            row=database.getCompanyMapping("reuters", self.state["coid"])
#            if row is None:
#                util.warning("Unmappable company {}".format(self.state["coid"]))
#                self.coId=-1
#                return
#            else:
#                self.coId=row["compustat"]
                
        self.processCalls = self.processCalls + 1
        
        rkd = int(self.state["coid"])
        broker = "CONSENSUS"
        if self.state["estimateType"] == "period":
            date = int(self.state["endDate"])
            estimateName = self.state["estimate"] + "_" + self.state["periodType"] + "_CE"
        else:
            date = 0L
            estimateName = self.state["estimate"] + "_CE"
            
        for orig, stats in self.statistics.iteritems():
            orig = util.convert_date_to_millis(_date(orig))
            event = self.state["event"]
        
            if event in ("Refresh", "New", "Revise", "Historical-Insert", "Historical-Update"):
                #assert that they all have the same currency
                assert stats["High"][1] == stats["Low"][1] and stats["High"][1] == stats["Mean"][1] and stats["High"][1] == stats["Median"][1] and stats["High"][1] == stats["StdDev"][1]
                                
                data = xdrlib.Packer()
                data.pack_float(float(stats["High"][0]) * self.mult[self.state["unit"]])
                data.pack_float(float(stats["Low"][0]) * self.mult[self.state["unit"]])
                data.pack_float(float(stats["Mean"][0]) * self.mult[self.state["unit"]])
                data.pack_float(float(stats["StdDev"][0]) * self.mult[self.state["unit"]] if stats["StdDev"][0] != "NA" else 0.0)
                data.pack_float(float(stats["Median"][0]) * self.mult[self.state["unit"]])
                data.pack_int(int(stats["NumOfEsts"][0]))
                currency = stats["High"][1]
                timestamp = self.timestamp if self.backfill == 0 else orig
                
                if event == "Revise":
                    oldOrig = _getMostRecentLiveOrig(rkd, self.source, estimateName, broker, date, "b")
                    if oldOrig is not None:
                        database.insertCoEstimateFlags(rkd, self.source, estimateName, "b", broker, date, oldOrig, orig, 'T', timestamp, None, self.backfill)
                elif event == "Historical-Update":
                    database.deleteCoEstimateFlags(rkd, self.source, estimateName, "b", broker, date, orig, timestamp)
                
                database.insertCoEstimate(rkd, self.source, estimateName, "b", broker, date, orig, data.get_buffer(), currency, timestamp, None, self.backfill)
                #database.insertCoEstimateFlags(self.coId,self.source,estimateName,"b",broker,date,orig,orig,'C',timestamp,None,self.backfill)
                
                #assert that they all have the same expir
                assert stats["High"][2] == stats["Low"][2] and stats["High"][2] == stats["Mean"][2] and stats["High"][2] == stats["Median"][2] and stats["High"][2] == stats["StdDev"][2]
                
                expir = None if stats["High"][2] is None else util.convert_date_to_millis(_date(stats["High"][2]))
                if expir is not None:
                    timestamp = self.timestamp if self.backfill == 0 else expir
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "b", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
            elif event in ("Stop"):
                #assert that they all have the same expir
                assert stats["High"][2] == stats["Low"][2] and stats["High"][2] == stats["Mean"][2] and stats["High"][2] == stats["Median"][2] and stats["High"][2] == stats["StdDev"][2]
                
                expir = util.convert_date_to_millis(_date(stats["High"][2]))
                timestamp = self.timestamp if self.backfill == 0 else expir
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "b", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
            elif event in ("Historical-Delete"):
                timestamp = self.timestamp if self.backfill == 0 else orig
                database.deleteCoEstimate(rkd, self.source, estimateName, "b", broker, date, orig, timestamp)
                database.deleteCoEstimateFlags(rkd, self.source, estimateName, "b", broker, date, orig, timestamp)
            else:
                util.error("Unknown command in ConsensusEstimatesHandler: {}".format(event))
                raise Exception  
                
def _getMostRecentLiveOrig(rkd, source, name, broker, date, datatype):
        assert datatype in ("n", "b", "d")
        
        table = database.CO_ESTIMATES + datatype
        measureCode = database.getAttributeType(name, source, datatype, table)
        brokerid = database.getBrokerId(source, broker, None)

        row = database.execute("SELECT orig FROM {} WHERE rkd=%(rkd)s AND type=%(type)s AND brokerid=%(brokerid)s AND date=%(date)s AND died IS NULL ORDER BY orig DESC,born DESC LIMIT 1".format(table), {"rkd":rkd, "type":measureCode, "date":date, "brokerid":brokerid}).fetchone()
                
        if row is None:
            return None
        else:
            return row["orig"]
        
class DetailedRatingsHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        self.state = {}

        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
        self.processCalls = 0
        
    def startElement(self, name, att):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = att["code"]
        elif name == "recommendation":
            self.position[name]=True
            self.state["recommendationType"] = att["type"]
        elif name == "broker":
            self.position[name]=True
            self.state["broker"] = att["brokerId"]
        elif name == "recValue":
            self.position[name]=True
            self.state["orig"] = att["orig"]
            self.state["expir"] = att.get("expir", None)
            self.state["confirmations"] = []
            self.state["suppressions"] = []
        elif name == "opinion" and att["set"] == "STD":
            self.position[name]=True
            self.state["recommendation"] = att["code"]
        elif name == "confirmationDate":
            self.position[name] = True
            self.state["confDate"] = ""
        elif name == "suppressFlag":
            self.position[name]=True
            self.state["suppressions"].append((att["orig"], att.get("expir", None)))
            
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "recommendation":
            #pass
            self.position[name]=False
        elif name == "broker":
            #pass
            self.position[name]=False
        elif name == "recValue":
            #pass
            self.position[name]=False
            self.__process()
        elif name == "opinion":
            #pass
            self.position[name]=False
        elif name == "confirmationDate":
            self.position[name] = False
            self.state["confirmations"].append(self.state["confDate"])
        elif name == "suppressFlag":
            #pass
            self.position[name]=False

    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
        elif self.position.get("confirmationDate", False):
            self.state["confDate"] += data
            
    def endDocument(self):
        pass
        #print datetime.datetime.now(),self.state["coid"],self.processCalls
            
    def __process(self):
        if self.state["recommendationType"] != "STOPINION":
            return
        
#        if self.coId is not None and self.coId<0: #previously failed to identify mapping:
#            return
#        elif self.coId==None:
#            row=database.getCompanyMapping("reuters", self.state["coid"])
#            if row is None:
#                util.warning("Unmappable company {}".format(self.state["coid"]))
#                self.coId=-1
#                return
#            else:
#                self.coId=row["compustat"]

        self.processCalls = self.processCalls + 1
        rkd = int(self.state["coid"])
        broker = self.state["broker"]
        date = 0L
        estimateName = "RECOMMENDATION" + "_DE"
        #orig, expir
        orig = util.convert_date_to_millis(_date(self.state["orig"]))
        expir = None if self.state["expir"] is None else util.convert_date_to_millis(_date(self.state["expir"]))
        #event
        event = self.state["event"]
        
        if event in ("Refresh", "New", "Revise", "Historical-Insert", "Historical-Update"):
            #get data
            value = int(self.state["recommendation"])
            currency = 'NA'
            
            timestamp = self.timestamp if self.backfill == 0 else orig
            
            if event == "Revise": #do it first to protect ourselves from stupid reuters, in case it inserts and revises something in the sam e file
                oldOrig = _getMostRecentLiveOrig(rkd, self.source, estimateName, broker, date, "n")
                if oldOrig is not None:
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, oldOrig, orig, 'T', timestamp, None, self.backfill)
            elif event == "Historical-Update":
                database.deleteCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
                        
            #insert start
            database.insertCoEstimate(rkd, self.source, estimateName, "n", broker, date, orig, value, currency, timestamp, None, self.backfill)
            #database.insertCoEstimateFlags(self.coId, self.source, estimateName, "n", broker, date, orig, orig, 'C', timestamp, None, self.backfill)
                        
            #insert flags
            #confirmations
            for confirmDate in self.state["confirmations"]:    
                confirmDate = util.convert_date_to_millis(_date(confirmDate))
                timestamp = self.timestamp if self.backfill == 0 else confirmDate
                if confirmDate != orig: #optimization
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, confirmDate, 'C', timestamp, None, self.backfill)
                
            #suppressions
            for suppressRange in self.state["suppressions"]:
                suppressStart = util.convert_date_to_millis(_date(suppressRange[0]))
                suppressEnd = None if suppressRange[1] is None else util.convert_date_to_millis(_date(suppressRange[1]))
                
                timestamp = self.timestamp if self.backfill == 0 else suppressStart
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressStart, 'S', timestamp, None, self.backfill)
                
                if suppressEnd is not None:
                    timestamp = self.timestamp if self.backfill == 0 else suppressEnd
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressEnd, 'U', timestamp, None, self.backfill)

            if expir is not None:
                timestamp = self.timestamp if self.backfill == 0 else expir
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill) 
        elif event in ("Stop"):
            timestamp = self.timestamp if self.backfill == 0 else expir
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
            #stops are also associated with suppressions. since we should already have these (historical) suppressions, we do not process them 
        elif event in ("Confirm"):            
            #assert that there is a single confirmation
            assert len(self.state["confirmations"]) == 1
            
            for confirmDate in self.state["confirmations"]:    
                confirmDate = util.convert_date_to_millis(_date(confirmDate))
                timestamp = self.timestamp if self.backfill == 0 else confirmDate    
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, confirmDate, 'C', timestamp, None, self.backfill)
        elif event in ("Suppress"):
            #assert that there is a single suppression
            assert len(self.state["suppressions"]) == 1
            
            suppressDate = self.state["suppressions"][-1][0]
            suppressDate = util.convert_date_to_millis(_date(suppressDate))
            timestamp = self.timestamp if self.backfill == 0 else suppressDate
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, suppressDate, 'S', timestamp, None, self.backfill)
        elif event in ("Unsuppress"):
            #assert that there is a single suppression
            assert len(self.state["suppressions"]) == 1
            
            unsuppressDate = self.state["suppressions"][-1][1]
            unsuppressDate = util.convert_date_to_millis(_date(unsuppressDate))
            timestamp = self.timestamp if self.backfill == 0 else unsuppressDate
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, unsuppressDate, 'U', timestamp, None, self.backfill)
        elif event in ("Historical-Delete"):
            #delete start
            timestamp = self.timestamp if self.backfill == 0 else orig
            database.deleteCoEstimate(rkd, self.source, estimateName, 'n', broker, date, orig, timestamp)
            database.deleteCoEstimateFlags(rkd, self.source, estimateName, 'n', broker, date, orig, timestamp)
        else:
            util.error("Unknown command in DetailedEstimatesHandler: {}".format(event))
            raise Exception
                
class ConsensusRatingsHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        self.state = {}

        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
        self.processCalls = 0
        
    def startElement(self, name, att):
        if name == "coId":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = att["code"]
        elif name == "consOpValue" and att["type"] == "MeanRating":
            self.position[name] = True
            self.state["orig"] = att["orig"]
            self.state["expir"] = att.get("expir", None)
        elif name == "consValue" and self.position.get("consOpValue", False):
            self.position[name] = True
            self.state["value"] = ""
   
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            #pass
            self.position[name]=False
        elif name == "consOpValue" and self.position.get("consOpValue", False):
            self.position[name] = False
            self.__process()
        elif name == "consValue" and self.position.get("consOpValue", False):
            self.position[name] = False
            
    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
        elif self.position.get("consValue", False):
            self.state["value"] += data
            
    def endDocument(self):
        pass
        #print datetime.datetime.now(),self.state["coid"],self.processCalls
        
    def __process(self):
#        if self.coId is not None and self.coId<0: #previously failed to identify mapping:
#            return
#        elif self.coId==None:
#            row=database.getCompanyMapping("reuters", self.state["coid"])
#            if row is None:
#                util.warning("Unmappable company {}".format(self.state["coid"]))
#                self.coId=-1
#                return
#            else:
#                self.coId=row["compustat"]
                
        self.processCalls = self.processCalls + 1
        
        rkd = int(self.state["coid"])
        broker = "CONSENSUS"
        date = 0L
        estimateName = "RECOMMENDATION" + "_CE"
        orig = util.convert_date_to_millis(_date(self.state["orig"]))
        expir = None if self.state["expir"] is None else util.convert_date_to_millis(_date(self.state["expir"]))
        event = self.state["event"]
        
        if event in ("Refresh", "Historical-Insert", "New", "Revise", "Historical-Update"):
            value = float(self.state["value"]) 
            
            timestamp = self.timestamp if self.backfill == 0 else orig
            
            if event == "Revise": #do it first to protect ourselves from stupid reuters, in case it inserts and revises something in the sam e file
                oldOrig = _getMostRecentLiveOrig(rkd, self.source, estimateName, broker, date, "n")
                if oldOrig is not None:
                    database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, oldOrig, orig, 'T', timestamp, None, self.backfill)
            elif event == "Historical-Update":
                database.deleteCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
            
            database.insertCoEstimate(rkd, self.source, estimateName, "n", broker, date, orig, value, "NA", timestamp, None, self.backfill)
            #database.insertCoEstimateFlags(self.coId, self.source, estimateName, "n", broker, date, orig, orig, 'C', timestamp, None, self.backfill)
            
            if expir is not None:
                timestamp = self.timestamp if self.backfill == 0 else expir
                database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
        elif event in ("Stop"):
            timestamp = self.timestamp if self.backfill == 0 else expir
            database.insertCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, expir, 'T', timestamp, None, self.backfill)
        elif event in ("Historical-Delete"):
            timestamp = self.timestamp if self.backfill == 0 else orig
            database.deleteCoEstimate(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
            database.deleteCoEstimateFlags(rkd, self.source, estimateName, "n", broker, date, orig, timestamp)
        else:
            util.error("Unknown command in ConsensusRatingsHandler: {}".format(event))
            raise Exception  
        
        
class IncCompanyHandler(xml.sax.handler.ContentHandler):
    def __init__(self, timestamp, backfill, source):
        self.position = {}
        self.state = {}

        self.timestamp = timestamp
        self.backfill = backfill
        self.source = source
        
        self.processCalls = 0
        
    def startElement(self, name, att):
        if name == "coId" and att["type"] == "XRef":
            self.position[name] = True
            self.state["coid"] = ""
        elif name == "event":
            self.position[name]=True
            self.state["event"] = att["code"]
            self.state["asOf"] = att["asOf"]
            self.state["splitdates"]=[]
            self.state["splitfactors"]=[]
        elif name == "split":
            self.position[name]=True
            self.state["splitdates"].append(att["dated"])
        elif name == "factor":
            self.position[name] = True
            self.state["factor"] = ""
            
    def endElement(self, name):
        if name == "coId":
            self.position[name] = False
        elif name == "event":
            self.position[name]=False
            self.__process()
        elif name == "split":
            self.position[name]=False
        elif name == "factor":
            self.position[name] = False
            self.state["splitfactors"].append(float(self.state["factor"]))
            
    def characters(self, data):
        if self.position.get("coId", False):
            self.state["coid"] += data
        elif self.position.get("factor", False):
            self.state["factor"] += data
            
    def endDocument(self):
        pass
        
    def __process(self):
        assert self.state["event"] in ("Historical-Update","Refresh","New","Stop")
        assert len(self.state["splitdates"])==len(self.state["splitfactors"])
        
        if len(self.state["splitdates"])==0:
            return
            
        rkd = int(self.state["coid"])
        timestamp=self.timestamp
        table=database.REUTERS+"split"
        attType=database.getAttributeType("SPLIT", self.source, "n", table)
        #delete all previous splits associated with rkd
        database.updateRows(table, {"rkd":rkd}, {"died" : timestamp})
        #reinsert
        for date,rate in zip(self.state["splitdates"],self.state["splitfactors"]):
            intdate=int(_date(date).strftime("%Y%m%d"))
            born=timestamp if self.backfill==0 else util.convert_date_to_millis(_date(date))
            assert self.backfill==1 or born>=timestamp
            updates=database.insertTimelineRow(table, {"rkd":rkd,"date":intdate}, {"rate":rate,"backfill":self.backfill},born,None,util.dict_fields_eq_num_stable)
            database.updateAttributeStats(attType, *updates)
            
def verifyMappings(filepath, source):
    return process(filepath, source, True)
            
def process(filepath, source, verifyOnly=False):    
    fileInfo = datafiles.read_info_file(filepath)
        
    if source == "rkd_refinfo":
#        type=filepath.split("/")[-1].split("_")[2]
#        if type=="f": return
        
        if fileInfo['date_last_absent'] is None:
            backfill = 1
            #timestamp=util.convert_date_to_millis(fileInfo["date_modified"])
        else:
            backfill = 0
            #timestamp=util.convert_date_to_millis(fileInfo["date_first_present"])
        date = filepath.split("/")[-1].split("_")[3]
        timestamp = util.convert_date_to_millis(date)
    elif source == "rkd_fpro_hist":
        backfill = 1
        timestamp = util.convert_date_to_millis(fileInfo["date_first_present"])
    elif source in ("rkd_fpro_cur", "rkd_fpro_inc"):
        if fileInfo['date_last_absent'] is None:
            #print "Current or incremental files cannot be backfilled"
#            return
#            raise Exception
            backfill = 0
            timestamp = util.convert_date_to_millis(fileInfo["date_modified"])
        else:
            backfill = 0
            timestamp = util.convert_date_to_millis(fileInfo["date_first_present"])
    
    database.setAttributeAutoCreate(True)
    database.setBrokerAutoCrate(True)
    database.setCurrencyAutoCreate(True)

    if not zipfile.is_zipfile(filepath):
        util.warning("Not a zipfile: {}".format(filepath))
        return

    zf = zipfile.ZipFile(filepath, "r") #the zip archive
    fileNames = zf.namelist()
        
    ###### MAPPINGS VERIFYCATION CODE ######
    coidInconsistencies = []
    secidInconcistencies = []
    #######################################
    
    counter = 0;
    for fileName in fileNames:         
        if source == "rkd_refinfo":
            handler = CompanyHandler(timestamp, backfill, source, filepath, verifyOnly)
        elif source == "rkd_fpro_cur" and "PM" in filepath: #from the current snapshot, only process the period models
            handler = PeriodModelHandler(timestamp, backfill, source)
        elif source == "rkd_fpro_inc" and "ID" in filepath: #skip end of day incremental updates, process the intra day ones
            continue
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "AC" in filepath:
            handler = ActualsHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "BR" in filepath:
            handler = BrokerHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "PM" in filepath:
            handler = PeriodModelHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "DE" in filepath:
            handler = DetailedEstimatesHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "CE" in filepath:
            handler = ConsensusEstimatesHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "RD" in filepath:
            handler = DetailedRatingsHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "CR" in filepath:
            handler = ConsensusRatingsHandler(timestamp, backfill, source)
        elif source in ("rkd_fpro_hist", "rkd_fpro_inc") and "CO" in filepath:
            handler = IncCompanyHandler(timestamp, backfill, source)
        else:
            continue
        
        if verifyOnly:
            assert isinstance(handler, CompanyHandler)
        
        file = zf.open(fileName)
        
        parser = xml.sax.make_parser()
        parser.setContentHandler(handler)
        parser.parse(file)

        ####### VERIFY MAPPINGS CODE #######
        if verifyOnly:
            coidInconsistencies.extend(handler.coidInconcistencies)
            secidInconcistencies.extend(handler.secidInconsistencies)
        #######

        file.close()
        #break
        counter = counter + 1
#        if counter==100:
#            break
    
    zf.close()
    
    ####### VERIFY MAPPINGS CODE #######
    if verifyOnly:
        return (coidInconsistencies, secidInconcistencies)
    #######

if __name__ == "__main__":
    newdb.init_db(os.environ["SEC_DB_CONFIG_FILE"])
    database = newdb.get_db()
    try:
        files=database.getProcessedFilesTimeOrdered("rkd_fpro_cur")
        
        procFiles = set()
        for row in database.execute("SELECT * from tmp_files").fetchall():
            procFiles.add(row["path"])
        
        for file in files:
            if file in procFiles:
                continue
            
            if not file.count("PM")>0:
                continue
            
            filepath = "/apps/ase/data/reuters/rkd_fpro_cur/" + file
            if not os.path.exists(filepath):
                util.info("skipping file " + filepath)
                continue
            
            util.info("Processing file " + filepath)
            database.start_transaction()
            process(filepath, "rkd_fpro_cur")
            database.execute("INSERT INTO tmp_files VALUES('{}')".format(file))
            database.commit()   

        #process("/apps/ase/data//reuters/rkd_fpro_hist/2008/09/27/200809270000PMHW.zip.a2b06120","rkd_fpro_hist")
    except:
        database.rollback()
        raise
    else:
        database.commit()
        #database.rollback()
