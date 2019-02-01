import asyncore, socket, yaml
import errno
import util

class listener ( object ):
    def __init__(self, onidle):
        self.onidle = onidle

    def handle_server(self, srv):
        print("SRV  %(name)s" % srv)
        self.trader.status()

    def handle_trade(self, trd):
        print("FILL %(symbol)5s %(fill-size)4d @%(fill-price).2f -> pos:%(position)+d  qtyLeft:%(qtyLeft)+d [orderId = %(orderID)]" % trd)

    def handle_info(self, info):
        print("INFO %(symbol)5s Halt: %(halt) pos:%(position)+%d / qtyLeft:%(qtyLeft)+%d" % info)

    def handle_error(self, err):
        print("ERR  %(error)s = %(reason)s (msg %(message-name)s | field %(field)s | sym %(symbol)s" % err)

    def handle_message(self, m):
        for k, v in m.items():
            print("%s: %s" % (k, v))
    def idle(self): 
        self.onidle()


class channel ( asyncore.dispatcher ):
    '''Channel for sending and receiving Guillotine messages asynchronously.'''

    # internal functions and callbacks
    def sendmsg (self, message, **fields ):
        fields['message'] = message
        for k, v in fields.items():
            if v is None: del fields[k]
        self.obuf += (yaml.dump(fields) + "---\n")
    
    def dispatch (self, m):
        if type(m) is not dict:
            print("Error: expected message, got... this?")
            print(m)
        else:
            for l in self.ls:
                try:
                    msgtype = m['message']
                    if msgtype == self.expecting:
                        self.expecting = ''
                    getattr(l, 'handle_'+msgtype)(m)
                except (AttributeError, KeyError):
                    try:
                        l.handle_message(m)
                    except (AttributeError):
                        pass
                
    def recvmsg (self, str):
        msgs = yaml.safe_load_all(str)
        for m in msgs:
            if type(m) is dict:
                self.pending = False
                self.dispatch(m)
            elif type(m) is list:
                ct = len(m)
                for m1 in m:
                    ct = ct - 1
                    self.pending = (ct != 0)
                    self.dispatch(m1)
    
    def __init__(self, gtc):
        util.debug("Initializing channel")
        #asyncore.dispatcher.__init__(self, *args, **kwargs)
        asyncore.dispatcher.__init__(self)

        self.gtc = gtc
        self.ls = []
        self.ibuf = ""
        self.obuf = ""
        self.pending = False
        self.expecting = ''
        self.host = ""
        self.port = ""

    def handle_connect(self):
        pass

    def handle_error(self):
        raise

    def handle_read(self):
        cont = True
        while cont:
            try:
                readstr = self.recv(8*1024)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    break
                else:
                    raise
            cont = len(readstr) == 8*1024
            self.ibuf += readstr
        
        mx = self.ibuf.rfind('---\n')
        if mx != -1:
            self.pending_text = self.ibuf[0:mx]
            self.ibuf = self.ibuf[mx+4:]
            self.recvmsg(self.pending_text);
            self.pending_text = ""


    def busy(self):
        retVal = (self.pending or len(self.ibuf) != 0)
        if retVal:
            util.debug("Busy in channel " + str(self.host) + ":" + str(self.port))
        return retVal

    def waiting(self):
        retVal = self.expecting != ''
        if retVal:
            util.debug("Waiting in channel " + str(self.host) + ":" + str(self.port))
        return retVal

    def writable(self): 
        for l in self.ls:
            l.idle()
        return len(self.obuf) > 0

    def handle_write(self):
        sent = self.send(self.obuf)
        self.obuf = self.obuf[sent:]

    def handle_close(self):
        subject = "Sending halt message to all trade servers"
        msg = "Most likely cause: Trade server " + str(self.host) + ":" + str(self.port) + " went down."
        util.email(subject, msg)
        for chn in self.gtc.chns:
            if self == chn:
                self.gtc.chns.remove(chn)
                break
        
        self.close()
        self.gtc.halt()
        #raise Exception('Socket closed')

    def register(self, l):
        self.ls.append(l)

    def unregister(self, l):
        self.ls.remove(l)

    def connect (self, host, port, account, password=None, name=None, listenToBcast=0):
        self.host = host
        self.port = port        
        util.info("Connecting to guillotine on %s:%s %s %s" % (host, port, account, name))
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        asyncore.dispatcher.connect(self, (host, port))
        self.sendmsg('connect', account=account, password=password, name=name, listenToBcast=listenToBcast)
        self.expecting = 'server'
        self.isconnected = True

    def trade (self, symbol, qty, aggr, orderID):
        util.debug("sending trade message")
        self.sendmsg('trade', symbol=symbol, qty=qty, aggr=aggr, orderID=orderID)
        self.expecting = 'info'

    def status (self, symbol=None):
        util.debug("Requesting status")
        self.sendmsg('status', symbol=symbol)
        self.expecting = 'info'

    def stop (self, symbol=None):
        util.debug("Sending stop message")
        self.sendmsg('stop', symbol=symbol)
        self.expecting = 'info'

    def halt (self, symbol=None):
        util.debug("Sending halt message")
        self.sendmsg('halt', symbol=symbol)
        self.expecting = 'info'

    def resume (self, symbol=None):
        util.debug("Sending resume message")
        self.sendmsg('resume', symbol=symbol)
        self.expecting = 'info'


class multiplex_channel ( object ) :

    class linkage ( object ):
        def __init__(self, chn, symmap):
            self.chn = chn
            chn.register(self)
            self.symmap = symmap
            
        def handle_info(self, msg):
            symbol = msg['symbol']
            chn = self.symmap.get(symbol)
            if chn is None:
                self.symmap[symbol] = self.chn
            elif chn != self.chn:
                if symbol != 'SPY':
                    raise Exception('Duplicate symbol %s on %s and %s' % (symbol, chn.getpeername(), self.chn.getpeername()))
                
        def idle(self):
            pass

    def __init__ (self):
        util.debug("Initializing multiplex channel")
        self.ls = []
        self.chns = []
        self.symmap = {}

    def register (self, l):
        for chn in self.chns:
            chn.register(l)
        self.ls.append(l)

    def connect (self, servers, account, password=None, name=None, listenToBcast=0):
        for (host, port) in servers:
            chn = channel(self)
            multiplex_channel.linkage(chn, self.symmap)
            for l in self.ls:
                chn.register(l)
            chn.connect(host, port, account, password, name, listenToBcast)
            chn.status()
            self.chns.append(chn)

    def close (self):
        util.info("Closing multiplex channel")
        for chn in self.chns:
            chn.close()

    def busy (self):
        return any(map(lambda c: c.busy(), self.chns))

    def waiting (self):
        return any(map(lambda c: c.waiting(), self.chns))

    def trade(self, symbol, quantity, aggr=None, orderID=-1):
        util.debug("trade")
        if type(symbol) == list:
            for s in symbol:
                chn = self.symmap.get(s)
                if chn is not None:
                    chn.trade(s, quantity, aggr, orderID)
                else:
                    raise KeyError
        else:
            chn = self.symmap.get(symbol)
            if chn is not None:
                chn.trade(symbol, quantity, aggr, orderID)
            else:
                raise KeyError

    def test_trade(self, symbol, quantity, aggr=None, orderID=-1):
        util.debug("test trade")
        if type(symbol) == list:
            for s in symbol:
                chn = self.symmap.get(s)
                if chn is not None:
                    pass
                    #chn.trade(s, quantity, aggr, orderID)
                else:
                    raise KeyError
        else:
            chn = self.symmap.get(symbol)
            if chn is not None:
                #chn.trade(symbol, quantity, aggr, orderID)
                pass
            else:
                raise KeyError

    def do_over (self, action, symbol=None):
        if symbol is None:
            for chn in self.chns:
                getattr(chn, action)()
        elif type(symbol) == list:
            for s in symbol:
                getattr(self.symmap[s], action)(s)
        else:
            getattr(self.symmap[symbol], action)(symbol)

    def status (self, symbol=None):
        self.do_over('status', symbol)
        
    def stop (self, symbol=None):
        self.do_over('stop', symbol)
        
    def halt (self, symbol=None):
        self.do_over('halt', symbol)
        
    def resume (self, symbol=None):
        self.do_over('resume', symbol)



class simple_multiplex_channel ( object ) :

    def __init__ (self):
        util.debug("Initializing simple multiplex channel")
        self.ls = []
        self.chns = []

    def register (self, l):
        for chn in self.chns:
            chn.register(l)
        self.ls.append(l)

    def connect (self, servers, account, password=None, name=None, listenToBcast=0):
        for (host, port) in servers:
            chn = channel(self)
            for l in self.ls:
                chn.register(l)
            chn.connect(host, port, account, password, name, listenToBcast)
            chn.status()
            self.chns.append(chn)

    def close (self):
        util.info("Closing simple multiplex channel")
        for chn in self.chns:
            chn.close()

    def busy (self):
        return any(map(lambda c: c.busy(), self.chns))

    def waiting (self):
        return any(map(lambda c: c.waiting(), self.chns))

