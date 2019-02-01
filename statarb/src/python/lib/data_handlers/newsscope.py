import xml.sax
import xml.sax.handler
import os
import re
import newdb
import datetime
import datafiles
import util
import string
from collections import Counter
import sys
import gzip

NEWS_ATTRIBUTE_TABLE = "newsscope_attr"
NEWS_INFO_TABLE = "newsscope_info"
database = newdb.get_db()
INSERT_INTO_DB = True

number = "(C?\(?(down|up)? *[RC]?(CDN|EUR)?\$?[0-9]+([\.,][0-9]+)?( ?[%BMmCc]c?s?)? ?\)?|breakeven|flat)"
patterns = [] 
patterns.append(("RNEWS_REC_INIT", re.compile(".+ (Above Average|Accumulate|Outperform|Buy|Overweight).*", re.I), +1))
patterns.append(("RNEWS_REC_INIT", re.compile(".+ (Below Average|Underperform|Sell|Underweight).*", re.I), -1))
patterns.append(("RNEWS_REC_INIT", re.compile(".+ (In Line|Perform|Neutral|Hold|Equal Weight).*", re.I), 0))
patterns.append(("RNEWS_RUMORS", re.compile(".+ (climbs|rallies|jumps|moving higher|raises on|shares rise|movers higher|moves higher|moves off lows|moves up|shares active|ticks up|ticks higher|strength attributed to|up on|trades higher|trades up|spikes higher|moves to positive territory|spikes|begins to move higher|lifts|continues to rise|moves positive).*", re.I), +1))
patterns.append(("RNEWS_RUMORS", re.compile(".+ (weakness attributed to|moves lower|drops on).*", re.I), -1))
patterns.append(("RNEWS_HOT_1", re.compile(".+ (recieve[sd]?|receive[sd]?|issued) .*?(SEC|warning|subpoena|deficiency|delisting|non-?compliance).*", re.I), -1))
patterns.append(("RNEWS_HOT_1", re.compile(".+ (achieves?|granted|awarded|secures?|renews?|receive[sd]?|granted|expands?|wins?|recieve[sd]?|issues?|issued|presents?|obtains?|announces?|signs?|acquires?|enters?|initiates?|completes?) .*?(rights?|discovery|discovers|awarded|partnerships?|collaborations?|enrollment|agreements?|strategic partner|alliances?|expanded|license|proposals?|permits?|trials?|authorization|availability|certifications?|favorable|data|CE mark|investments?|payments?|extensions?|milestones?|allowances?|accreditations?|(new.*? business)|(oil|gas) reserves|grants?|FDA (priority|approval)|proceeds|royalty|royalties|SPA|([Cc]learance)|waiver|commitments|positive|patents?|contracts?|projects?|deal|orders?|(in (.+)? case)|design|progress|program|assignment|option|approval|settlement|permission|promising|significantly improved|launch|regains|unsolicited offer).*", re.I), +1))
patterns.append(("RNEWS_HOT_2", re.compile(".+ (to raise|raises|increases|to increase|initiates|raising|declares?|delcares?) .*dividend.*", re.I), +1))
patterns.append(("RNEWS_HOT_2", re.compile(".+ (cuts|to cut|to lower|lowers|decreases|suspends|plans to suspend|lowering) .*dividend.*", re.I), -1))
patterns.append(("RNEWS_HOT_3", re.compile(".+ (acquires|raises|acquired) .*stake.*", re.I), +1))
patterns.append(("RNEWS_HOT_3", re.compile(".+ (lowers|liquidn?ates|sell|sells|considering selling|sold) .*stake.*", re.I), -1))
patterns.append(("RNEWS_HOT_4", re.compile(".+ (recall(s?|ing|ed)|discontinu(ing|ed|es?)|lays off|questions efficacy|announces salary reductions|announces (possible )?compromise|lowers guidance|conditions to worsen|sees (.+)?revenue decline|to layoff|not confident|capacity down|(plummets?|sinks?|drops?|moves? lower|falls?|tumbles?|retreats?) (.+)?(after|following|on)|(to reduce|reduced) (distribution|workforce)|reductions (have been|will be) (implemented|likely)|enters into lease termination|loses to|sales (down|trends? worsens?|decreased)|(credit|ratings?) (may get )?(downgraded|lowered)|downgrades|to (cut|eliminate) ((approximately|roughly) )?(%s )?jobs|to stop offering|pullback in demand|curtails production|not in compliance|takes action against|injunction restrains|(Nasdaq|NASDAQ) (notice|notification)|(notice|notification) from (Nasdaq|NASDAQ)|losses|damaged|misses|lawsuit|fraud|halts).*" % number, re.I), -1))
patterns.append(("RNEWS_HOT_4", re.compile("(.+)?(launches new|expects increased demand|raises %s|resum(ed|es?|ing)|licenses? out|licenses technology|delivers|begins delivery|settles? (.+)?litigation|increases (.+)?distribution|raises guidance|approached by potential buyers|removed from CreditWatch|sales up|sales trends (.+)?improve|successfully|could expand|rules in favor for|expects .+ orders|confident|closer to Phase|remains on track|on track to|to manufacture|expects (.+)?to improve|expects strong cash flow|expects production to increase|reports? positive|reports? preliminary data|receives offer|expenses to decline|says .+ now available in|expands? distribution|selected by|selected for|sales increased|will improve|positioned for (.+)?recovery|performance strong|(credit|ratings?) (increased|raised|upgraded)|prepared to weather|continues to increase output|expanding capacity|order (.+)?delivered|(rises?|raises?|gains?|spikes?|advances?|rallies?|soars?|surges?|climbs?|trades? higher) (.+)?(on|following|after)|deploys|to deploy|provides|to provide|extend development|FDA approves|to recognize %s gain|buys %s shares|invests in second phase|shares rise|reaches agreement|sees growth|adds significant production).*" % (number, number, number), re.I), +1)) 
#patterns["14"] = (re.compile(".+ price target to (?P<target>%s) from (?P<oldtgt>%s) at .+" % (number, number), re.I))
patterns.append(("RNEWS_REC", re.compile(".+ (raises price target|is a good deal|underappreciated|likely (to )?be approved|should (grow|move higher)|momentum is continuing|weakness is an overreaction|move is positive|reported (solid|excellent)|pursuing correct|outlook remains positive|will be helped|[cs]hould be better than expected|valuation compelling|has been (very )?positive|should stay strong|are top ideas|checks indicate healthy|should benefit|recommends a long|fundamentals still solid|well-positioned to (outperform|benefit)|shares oversold|should be bought|creates (a )?buying opportunity|a (strong )?buying opportunity|highly attractive|should sell better|problem is fixable|down on misguided|sell-off is overdone|positive news|can achieve|(is|are) strong|outlook (is )?boosted|guidance (is )?(likely )?conservative|should gain|reiterated (Outperform|Buy)|should be owned|poised|be able to overcome|has (good|best) prospects|significantly undervalued|added to Top Picks|remains? undervalued|results bode well|upgraded|valuation (is )?(still )?(remains )?attractive|attractively valued|raise is likely|added to (short[- ]term )?buy list|added to .+ List|added to .+ as a buy|shares defended at|should report (strong|better|stronger|solid)|margins strong|continue to generate (strong )?growth|(shown|shows) signs of improvement|estimates raised|strategy worked|results will likely be solid|named a long|weakness a buying opportunity|risk/reward (ratio )?(is )?(attractive|positive|favorable)|upgraded|mentioned positively|target raised|supports approval|has an approvable|still approvable).*", re.I), +1))
patterns.append(("RNEWS_REC", re.compile(".+ (target cut|reiterated Sell|should report weak(er)?|shares likely to be weak|growth seems to be slowing|estimates (reduced|trimmed)|fundamentals do not support|(will|appears to) be hurt|should be sold|valuations? (is )?(still )?(remains )?unattractive|(should|will) encounter more competition|expectations could be aggressive|remains overvalued|indicate slowing|likely to lose|faces risk|should report (.+)?weaker|will face (.+)?slowdown|sales ((appear to be|are) )?deteriorating|downgraded|estimates lowered|removed from .+ List|removed from Top Picks|still likely to fail|likely to stimulate fear|target lowered|a Sell at|lowers estimates|removed from (short[- ]term )?buy list).*", re.I), -1))
patterns.append(("RNEWS_ALL", re.compile(".+ buyback.*", re.I), +1))

def reutersDate(date):
    return datetime.datetime.strptime(date[0:19], "%Y-%m-%dT%H:%M:%S")

#remove non printable characters that can have creeped in name
def printableString(name):
    if name is None:
        return None
    #check first if it is printable
    printable = reduce(lambda x, y: x and (y in string.printable), name, True)
    if printable:
        return name
    else:
        newName = [c for c in name if c in string.printable]
        newName = ''.join(newName).strip()
        return newName

def extract(headline):
    global patterns
    
    matches = []
    for name, pattern, score in patterns:
        if  pattern.match(headline) is not None:
            matches.append((name, score))
    return matches
    
class NewsHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.position = {}
        self.state = {}
        self.state["rics"] = []
        
    def startElement(self, name, attributes):
        if name == "memberOf":
            self.position[name] = True
            self.state["story"] = attributes["qcode"].split(":")[1] if "qcode" in attributes else None
        elif name == "versionCreated":
            self.position[name] = True
            self.state["version_ts"] = ""
        elif name == "firstCreated":
            self.position[name] = True
            self.state["first_ts"] = ""
        elif name == "headline":
            self.position[name] = True
            self.state["headline"] = ""
        elif name == "language":
            self.position[name] = True
            self.state["language"] = attributes.get("tag", None)
        elif name == "subject":
            self.position[name] = True
            if attributes.get("qcode", "").startswith("rtrs.RICS"):
                self.state["rics"].append(attributes.get("qcode").split(":")[1])
        elif name == "inlineXML":
            self.position[name] = True
            self.state["innerXML"] = ""
    
    def endElement(self, name):
        if name == "memberOf":
            self.position[name] = False
        elif name == "versionCreated":
            self.position[name] = False
        elif name == "firstCreated":
            self.position[name] = False
        elif name == "headline":
            self.position[name] = False
        elif name == "language":
            self.position[name] = False
        elif name == "subject":
            self.position[name] = False
        elif name == "inlineXML":
            self.position[name] = False
    
    def characters(self, data):
        if self.position.get("versionCreated", False):
            self.state["version_ts"] += data
        elif self.position.get("firstCreated", False):
            self.state["first_ts"] += data
        elif self.position.get("headline", False):
            self.state["headline"] += data
        elif self.position.get("innerXML", False):
            self.state["innerXML"] += data
    
    def endDocument(self):
        pass
        
    def getInfo(self):
        data = {}
        data["version_ts"] = self.state.get("version_ts", None)
        data["first_ts"] = self.state.get("first_ts", None)
        data["storyid"] = self.state.get("story", None)
        data["language"] = self.state.get("language", None)
        data["headline"] = self.state.get("headline", None)
        data["rics"] = self.state.get("rics", [])
        return data

def process(filepath, source):
    database.setAttributeAutoCreate(True)
    fileInfo = datafiles.read_info_file(filepath)
    if fileInfo['date_last_absent'] is None:
        backfill = 1
        fileDate = filepath.split("/")[-1]
        fileDate = datetime.datetime.strptime(fileDate[0:15], "%Y%m%d-%H%M%S")
        born = util.convert_date_to_millis(fileDate)
    else:
        backfill = 0
        born = util.convert_date_to_millis(fileInfo["date_first_present"])
    
    file = gzip.open(filepath, 'r')
    file.readline()
    
    handler = NewsHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.parse(file)
    
    data = handler.getInfo()
    if data["language"] == "en":
        storyid = data["storyid"]
        version_ts = util.convert_date_to_millis(reutersDate(data["version_ts"]))
        first_ts = util.convert_date_to_millis(reutersDate(data["first_ts"]))
        headline = printableString(data["headline"]).strip() if data["headline"] is not None else None
        rics = data["rics"]
        
        updates = database.insertTimelineRow(NEWS_INFO_TABLE, {"storyid": storyid, "version": version_ts}, {"headline": headline}, born)
        for ric in rics:
            type = database.getAttributeType("RNEWS_PRESENCE", "newsscope", "n", NEWS_ATTRIBUTE_TABLE)
            updates = database.insertTimelineRow(NEWS_ATTRIBUTE_TABLE, {"ric": ric, "storyid": storyid, "date":first_ts, "type":type}, {"value": 1, "backfill": backfill, "version": version_ts}, born)
            database.updateAttributeStats(type, *updates)

        #remember to add back in where RIC bases are the same...
        ricsPrefix = [ric.split(".")[0] for ric in rics]
        if len(rics) == 1 or (len(ricsPrefix) > 0 and all([ric == ricsPrefix[0] for ric in ricsPrefix])):
            matches = extract(headline)
            if not len(matches) > 0:
                return
            
            for name, score in matches:
                type = database.getAttributeType(name, "newsscope", "n", NEWS_ATTRIBUTE_TABLE)
                for ric in rics:
                    updates = database.insertTimelineRow(NEWS_ATTRIBUTE_TABLE, {"ric": ric, "storyid": storyid, "date": first_ts, "type":type}, {"value":score, "backfill": backfill, "version": version_ts}, born)
                    database.updateAttributeStats(type, *updates)
                    
            totalScore = sum([score for name, score in matches])
            type = database.getAttributeType("RNEWS_TOTAL", "newsscope", "n", NEWS_ATTRIBUTE_TABLE)
            for ric in rics:
                updates = database.insertTimelineRow(NEWS_ATTRIBUTE_TABLE, {"ric": ric, "storyid": storyid, "date": first_ts, "type":type}, {"value":totalScore, "backfill": backfill, "version": version_ts}, born)
                database.updateAttributeStats(type, *updates)
                            
def processForStats(filepath, stats):    
    file = gzip.open(filepath, 'r')
    file.readline()
    
    handler = NewsHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.parse(file)
    
    data = handler.getInfo()
    if data["language"] == "en":
        storyid = data["storyid"]
        version_ts = util.convert_date_to_millis(reutersDate(data["version_ts"]))
        headline = printableString(data["headline"])
        rics = data["rics"]
        
        for ric in rics:
            stats[("RNEWS_PRESENCE", 1)] += 1
        
        if len(rics) == 1:
            matches = extract(headline)
            for name, score in matches:
                stats[(name, score)] += 1
                
    file.close()
    
if __name__ == "__main__":
    outputFile = sys.argv[1]
    dir = "/apps/ase/data/newsscope/news"
    stats = Counter()
    for daydir in sorted(os.listdir(dir)):
        for file in sorted(os.listdir(dir + "/" + daydir)):
            if "info" in file:
                continue
            if not re.match("\d{8}-\d{6}-.*", file):
                continue
            print "Processing", "/".join((dir, daydir, file))
            processForStats("/".join((dir, daydir, file)), stats)
    
    with open(outputFile, 'w') as file:
        for name, score in sorted(stats.keys()):
            count = stats[(name, score)]
            file.write("{}|{}|{}\n".format(name, score, count))
    
    #output stats
    
#if __name__ == "__main__":
#    newdb.init_db()
#    database=newdb.get_db()
#    database.setAttributeAutoCreate(True)
#    try:
#        database.start_transaction()
#        dir = "/apps/ase/data/newsscope/news"
#        for daydir in sorted(os.listdir(dir)):
#            for file in sorted(os.listdir(dir+"/"+daydir)):
#                if "info" in file:
#                    continue
#                if not re.match("\d{8}-\d{6}-.*", file):
#                    continue
#                print "Processing", "/".join((dir, daydir, file))
#                process("/".join((dir, daydir, file)), None)
#    except:
#        database.rollback()
#        raise
#    else:
#        #database.commit()
#        database.rollback()
