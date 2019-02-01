import re
import dateutil.parser
import pytz

import datafiles
import util
import newdb
import newdb.xrefsolve

database = newdb.get_db()
SOURCE = "fly"
number = "(C?\(?(down|up)? *[RC]?(CDN|EUR)?\$?[0-9]+([\.,][0-9]+)?( ?[%BMmCc]c?s?)? ?\)?|breakeven|flat)"
tcache = dict()

def handle_news(ticker, attr, date, val, born):        
    secid=database.getSecidFromXref("TIC", ticker, born, "compustat_idhist", newdb.xrefsolve.preferUS)
    if secid is None:
        util.warning("Failed to map ticker {}".format(ticker))
        return
    coid,issueid=database.getCsidFromSecid(secid)
    assert coid is not None    
    
    database.insertAttribute("co", "n", coid, date, SOURCE, attr, val, born, None, 0)
    #db.handle_attribute('co', 'n', tcache[ticker], attr, date, val, born, SOURCE)

def parse_grade(str, negative):
    value = None
    if str == "upgraded":
        value = 1
    elif str == "downgraded":
        value = -1
    else:
        assert False, 'Unknown grade'
    if negative is not None:
        value *= -1
    return value

def normalize_number(str):
    str = str.replace("cc", "c")
    str = str.replace(" ", "")
    str = str.replace("CDN", "")
    str = str.replace("EUR", "")
    str = str.replace("C", "")
    str = str.replace("R", "")
    str = str.replace("$", "")
    if str.startswith("(") or str.endswith(")"):
        str = "-" + str
        str = str.replace("(", "")
        str = str.replace(")", "")
    elif str.startswith("down"):
        str = str.replace("down", "")
        str = "-" + str
    elif str.startswith("up"):
        str = str.replace("up", "")
    str = str.replace(",", ".")
    if str.find("breakeven") != -1 or str.find("flat") != -1:
        return 0.0
    base = 1
    if str.endswith("c"):
        str = str[0:-1]
        base = 0.01
    elif str.endswith("cs"):
        str = str[0:-2]
        base = 0.01
    elif str.endswith("M") or str.endswith("m"):
        str = str[0:-1]
        base = 1000000
    elif str.endswith("B"):
        str = str[0:-1]
        base = 1000000000
    elif str.endswith("%"):
        str = str[0:-1]
        base = 1
    return float(str)*base

def process(filepath, source):
    info = datafiles.read_info_file(filepath)
    born_millis = util.convert_date_to_millis(info['date_first_present'])
    #db.insert_checks(next=True, prev=True)

    database.setAttributeAutoCreate(True)

    f = file(filepath, 'r')
    for line in f.readlines():
        line = line.rstrip("\n")

        # Parse story
        story = line.split("|")
        #secs = int(story[0][1:])
        #num = int(story[1])
        time = story[2][0:9]
        text = story[2][10:]

        local_date = info['date_first_present'].astimezone(pytz.timezone('US/Eastern'))
        date = dateutil.parser.parse(str(local_date)[0:11] + time)
        date_millis = util.convert_date_to_millis(date)

        sep = text.find(" - ")
        if sep == -1:
            sep = len(text)
        headline = text[0:sep]
        #body = text[sep+3:]

        category = story[3]
        tickers = story[4].split(";")

        # clean some crap out
        headline = headline.replace("'", "")
        headline = headline.replace("\"", "")
        headline = headline.replace("  ", " ")

        if category == 'Rec-Upgrade' or category == 'Rec-Downgrade':
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            if category == 'Rec-Upgrade':
                value = 1
            else:
                value = -1
            handle_news(tickers[0], 'FRATING', date_millis, value, born_millis)
            if len(tickers) > 1 and re.match(".+ (not|Not|NOT) .+", headline) != None:
                handle_news(tickers[1], 'FRATING', date_millis, -1*value, born_millis)

        elif category == "Rec-Initiate":
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            value = None
            if re.match(".+ (Above Average|Accumulate|Outperform|Buy|Overweight).*", headline):
                value = 1
            elif re.match(".+ (Below Average|Underperform|Sell|Underweight).*", headline):
                value = -1
            elif re.match(".+ (In Line|Perform|Neutral|Hold|Equal Weight).*", headline):
                value = 0
            if value is not None:
                handle_news(tickers[0], 'FRATING', date_millis, value, born_millis)
            else:
                util.warning('unmatched rec initiate')
                util.warning(headline+" "+ str(tickers))

        elif category == 'Rumors':
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY1', date_millis, i, born_millis)
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            value = None
            if re.match(".+ (climbs|rallies|jumps|moving higher|raises on|shares rise|movers higher|moves higher|moves off lows|moves up|shares active|ticks up|ticks higher|strength attributed to|up on|trades higher|trades up|spikes higher|moves to positive territory|spikes|begins to move higher|lifts|continues to rise|moves positive).*", headline):
                value = 1
            elif re.match(".+ (weakness attributed to|moves lower|drops on).*", headline):
                value = -1
            if value is not None:
                handle_news(tickers[0], 'FRUMOR', date_millis, value, born_millis)
            else:
                util.warning('unmatched rumor')
                util.warning(headline+" "+ str(tickers))

        elif category == 'Hot Stocks':
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY1', date_millis, i, born_millis)
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            value = None
            if re.match(".+ (recieve[sd]?|receive[sd]?|issued) .*?(SEC|warning|subpoena|deficiency|delisting|non-?compliance).*", headline): value = -1
            elif re.match(".+ (achieves?|granted|awarded|secures?|renews?|receive[sd]?|granted|expands?|wins?|recieve[sd]?|issues?|issued|presents?|obtains?|announces?|signs?|acquires?|enters?|initiates?|completes?) .*?(rights?|discovery|discovers|awarded|partnerships?|collaborations?|enrollment|agreements?|strategic partner|alliances?|expanded|license|proposals?|permits?|trials?|authorization|availability|certifications?|favorable|data|CE mark|investments?|payments?|extensions?|milestones?|allowances?|accreditations?|(new.*? business)|(oil|gas) reserves|grants?|FDA (priority|approval)|proceeds|royalty|royalties|SPA|([Cc]learance)|waiver|commitments|positive|patents?|contracts?|projects?|deal|orders?|(in (.+)? case)|design|progress|program|assignment|option|approval|settlement|permission|promising|significantly improved|launch|regains|unsolicited offer).*", headline): value = 1
            elif re.match(".+ (to raise|raises|increases|to increase|initiates|raising|declares?|delcares?) .*dividend.*", headline): value = 1
            elif re.match(".+ (cuts|to cut|to lower|lowers|decreases|suspends|plans to suspend|lowering) .*dividend.*", headline): value = -1
            elif re.match(".+ (acquires|raises|acquired) .*stake.*", headline): value = 1
            elif re.match(".+ (lowers|liquidn?ates|sell|sells|considering selling|sold) .*stake.*", headline): value = -1
            elif re.match(".+ (recall(s?|ing|ed)|discontinu(ing|ed|es?)|lays off|questions efficacy|announces salary reductions|announces (possible )?compromise|lowers guidance|conditions to worsen|sees (.+)?revenue decline|to layoff|not confident|capacity down|(plummets?|sinks?|drops?|moves? lower|falls?|tumbles?|retreats?) (.+)?(after|following|on)|(to reduce|reduced) (distribution|workforce)|reductions (have been|will be) (implemented|likely)|enters into lease termination|loses to|sales (down|trends? worsens?|decreased)|(credit|ratings?) (may get )?(downgraded|lowered)|downgrades|to (cut|eliminate) ((approximately|roughly) )?(%s )?jobs|to stop offering|pullback in demand|curtails production|not in compliance|takes action against|injunction restrains|(Nasdaq|NASDAQ) (notice|notification)|(notice|notification) from (Nasdaq|NASDAQ)|losses|damaged|misses|lawsuit|fraud|halts).*" % number, headline): value = -1
            elif re.match("(.+)?(launches new|expects increased demand|raises %s|resum(ed|es?|ing)|licenses? out|licenses technology|delivers|begins delivery|settles? (.+)?litigation|increases (.+)?distribution|raises guidance|approached by potential buyers|removed from CreditWatch|sales up|sales trends (.+)?improve|successfully|could expand|rules in favor for|expects .+ orders|confident|closer to Phase|remains on track|on track to|to manufacture|expects (.+)?to improve|expects strong cash flow|expects production to increase|reports? positive|reports? preliminary data|receives offer|expenses to decline|says .+ now available in|expands? distribution|selected by|selected for|sales increased|will improve|positioned for (.+)?recovery|performance strong|(credit|ratings?) (increased|raised|upgraded)|prepared to weather|continues to increase output|expanding capacity|order (.+)?delivered|(rises?|raises?|gains?|spikes?|advances?|rallies?|soars?|surges?|climbs?|trades? higher) (.+)?(on|following|after)|deploys|to deploy|provides|to provide|extend development|FDA approves|to recognize %s gain|buys %s shares|invests in second phase|shares rise|reaches agreement|sees growth|adds significant production).*" % (number, number, number), headline): value = 1
            if value is not None:
                handle_news(tickers[0], 'FHOT', date_millis, value, born_millis)
            else:
                util.warning('unmatched hot stocks')
                util.warning(headline+" "+ str(tickers))

        elif category == "Recommendations":
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY1', date_millis, i, born_millis)
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            if headline.find("price target to") != -1:
                m = re.match(".+ price target to (?P<target>%s) from (?P<oldtgt>%s) at .+" % (number, number), headline)
                if m is not None:
                    gd = m.groupdict()
                    target = normalize_number(gd['target'])
                    oldtgt = normalize_number(gd['oldtgt'])
                    if target > oldtgt:
                        value = 1
                    elif target < oldtgt:
                        value = -1
                    else:
                        value = 0
                    handle_news(tickers[0], 'FREC', date_millis, value, born_millis)
            else:
                value = None
                if re.match(".+ (raises price target|is a good deal|underappreciated|likely (to )?be approved|should (grow|move higher)|momentum is continuing|weakness is an overreaction|move is positive|reported (solid|excellent)|pursuing correct|outlook remains positive|will be helped|[cs]hould be better than expected|valuation compelling|has been (very )?positive|should stay strong|are top ideas|checks indicate healthy|should benefit|recommends a long|fundamentals still solid|well-positioned to (outperform|benefit)|shares oversold|should be bought|creates (a )?buying opportunity|a (strong )?buying opportunity|highly attractive|should sell better|problem is fixable|down on misguided|sell-off is overdone|positive news|can achieve|(is|are) strong|outlook (is )?boosted|guidance (is )?(likely )?conservative|should gain|reiterated (Outperform|Buy)|should be owned|poised|be able to overcome|has (good|best) prospects|significantly undervalued|added to Top Picks|remains? undervalued|results bode well|upgraded|valuation (is )?(still )?(remains )?attractive|attractively valued|raise is likely|added to (short[- ]term )?buy list|added to .+ List|added to .+ as a buy|shares defended at|should report (strong|better|stronger|solid)|margins strong|continue to generate (strong )?growth|(shown|shows) signs of improvement|estimates raised|strategy worked|results will likely be solid|named a long|weakness a buying opportunity|risk/reward (ratio )?(is )?(attractive|positive|favorable)|upgraded|mentioned positively|target raised|supports approval|has an approvable|still approvable).*", headline):
                    value = 1
                elif re.match(".+ (target cut|reiterated Sell|should report weak(er)?|shares likely to be weak|growth seems to be slowing|estimates (reduced|trimmed)|fundamentals do not support|(will|appears to) be hurt|should be sold|valuations? (is )?(still )?(remains )?unattractive|(should|will) encounter more competition|expectations could be aggressive|remains overvalued|indicate slowing|likely to lose|faces risk|should report (.+)?weaker|will face (.+)?slowdown|sales ((appear to be|are) )?deteriorating|downgraded|estimates lowered|removed from .+ List|removed from Top Picks|still likely to fail|likely to stimulate fear|target lowered|a Sell at|lowers estimates|removed from (short[- ]term )?buy list).*", headline):
                    value = -1
                if value is not None:
                    handle_news(tickers[0], 'FREC', date_millis, value, born_millis)
                else:
                    util.warning('unmatched recommendations')
                    util.warning(headline+" "+ str(tickers))

        elif category == 'Options':
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY1', date_millis, i, born_millis)
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            value = None
            if re.match(".+ puts? (options )?(more )?active.*", headline):
                value = -1
            elif re.match(".+ calls? (options )?(more )?active.*", headline):
                value = 1
            if value is not None:
                handle_news(tickers[0], 'FOPTION', date_millis, value, born_millis)
            else:
                util.warning('unmatched options')
                util.warning(headline+" "+ str(tickers))

        elif category == 'Earnings':
            for i, ticker in enumerate(tickers):
                handle_news(ticker, 'FLY1', date_millis, i, born_millis)
                handle_news(ticker, 'FLY2', date_millis, i, born_millis)
            headline = headline.replace("break-even", "breakeven")
            headline = headline.replace("break even", "breakeven")
            if headline.find("consensus") != -1:
                m = re.match(".+? (?P<reported>(%s(( to )|-))?%s) .*consensus.* (?P<consensus>%s)" % (number, number, number), headline)
                if m is not None:
                    gd = m.groupdict()
                    cons = normalize_number(gd['consensus'])
                    value = None
                    gd['reported'] = gd['reported'].replace("-", " to ")
                    if gd['reported'].find(" to ") != -1:
                        rvalues = gd['reported'].split(" to ")
                        rvalues[0] = normalize_number(rvalues[0])
                        rvalues[1] = normalize_number(rvalues[1])
                        replb = min(rvalues[0], rvalues[1])
                        repub = max(rvalues[0], rvalues[1])
                        if repub < cons:
                            value = -1
                        if replb > cons:
                            value = 1
                        else:
                            value = 0
                    else:
                        rvalue = normalize_number(gd['reported'])
                        if rvalue < cons:
                            value = -1
                        elif rvalue > cons:
                            value = 1
                        else:
                            value = 0
                    handle_news(tickers[0], 'FEARN', date_millis, value, born_millis)
                else:
                    if re.match(".+ (above|will exceed|should meet or beat|at least meet) .*consensus.*", headline) is not None:
                        handle_news(tickers[0], 'FEARN', date_millis, 1, born_millis)
                    elif re.match(".+ (below|not expected to meet) .*consensus.*", headline) is not None:
                        handle_news(tickers[0], 'FEARN', date_millis, -1, born_millis)
                    else:
                        util.warning('unmatched consensus')
                        util.warning(headline+" "+ str(tickers))

        elif category == 'Technical Analysis':
            pass

        elif category == 'Conference/Events':
            pass

        elif category == 'General news':
            pass

        elif category == 'Periodicals':
            pass

        elif category == 'Syndicate':
            value = None
            if re.match(".+ ([Tt]o [Ss]ell) .+", headline):
                value = -1
            if value is not None:
                handle_news(tickers[0], 'FSYND', date_millis, value, born_millis)
            else:
                util.warning('unmatched syndicate')
                util.warning(headline+" "+ str(tickers))

        else:
            util.warning('unknown category')
            util.warning(category+" "+headline+" "+ str(tickers))
            
if __name__=="__main__":
    newdb.init_db()
    database = newdb.get_db()
    try:
        database.start_transaction()
        process("/apps/ase/data/fly/fly/20110331/fly-20110331.690-697.txt.e3448def","fly")
    except:
        database.rollback()
        raise
    else:
        #database.commit()
        database.rollback()

