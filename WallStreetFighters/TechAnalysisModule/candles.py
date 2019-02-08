# coding: utf-8

"""Dane wejściowe do każdej funkcji to 4 tablice jednakowej długości przechowujące
kursy open, low, high, close. Parament trend oznacza to, w jakim trendzie się znajdujemy,
(rosnący lub malejący). Zgodnie z konwencją Pawła 1=trend rosnący, -1 malejący.

ACHTUNG !
indeksy wystąpienia formacji są zwracane w odniesieniu do przekazanych tablic, czyli
jeśli przekażemy ostatnie 10 elementów z tablicy 100 elementowej i dostaniemy indeksy
2,3 to znaczy że w pierwotnej tablicy to było na pozycjach 92, 93
"""

import trendAnalysis as trendA

CANDLE_MAX_LEN = 20 #maksymalna ilość świec, które bierzemy pod uwagę szukając formacji
STRONG_TREND=0.3 #wartość współczynnika kierunkowego prostej, powyżej którego traktujemy trend jako silny
STRAIGHT_TREND_VUL=0.05 #o ile wartości mogą odchylać się od regresji przy szukaniu luk
LONG_BODY=0.03  #parametr określający jaką różnicę mięczy O a C traktujemy jako dużą (3%)
SHORT_BODY=0.005    #parametr określający jaką różnicę mięczy O a C traktujemy jako małą (0,5%)
LOW_PART=0.25  #poniżej tej części wykresu szukamy luki startowej
HIGH_PART=0.75  #powyżej tej części wykresu szukamy luki wyczerpania


def findCandleFormations(O,H,L,C):
    """Szuka na wykresie formacji świecowych, dla każdej formacji która wystąpiła
    zwraca tablicę krotek ('nazwa',indeks rozpoczęcia, indeks zakończenia,wartość). Przy czym,
    dla każdej formacji jest co najwyżej jedna krotka z jej ostatnim wystąpieniem"""
    trend=trendA.optimizedTrend(C)
    if not (len(O)==len(H)==len(L)==len(C)):        
        return None
    result=[]
    if len(O)>CANDLE_MAX_LEN:
        offset=len(O)-CANDLE_MAX_LEN
        O=O[-CANDLE_MAX_LEN::1]
        H=H[-CANDLE_MAX_LEN::1]
        L=L[-CANDLE_MAX_LEN::1]
        C=C[-CANDLE_MAX_LEN::1]        
    else:
        offset=0       
    #print "trend= ",trend
    #print "offset= ", offset
    if trend==1:
        result.append(findBull3(O,H,L,C))
        result.append(findEveningStar(O,C))
        result.append(findDarkCloud(O,C))        
    else:
        result.append(findBear3(O,H,L,C))
        result.append(findMorningStar(O,C))
        result.append(findPiercing(O,C))        
    if result!=[]:
        #wartość jest odwrotnie proporcjonalna do tego, jak dawno wystąpiła formacja
        #żeby dawne wartości nie były zbyt małe, dzielimy przez 0.8*min(długość tablicy, CANDLE_MAX_LEN)
        result=[value for value in result if value != None]
        for formation in result:
            if offset==0:
                factor=len(O)
            else:
                factor=CANDLE_MAX_LEN
            value=formation[2]/(0.8*factor)
            if value>1:
                value=1
            formation=(formation[0],formation[1]+offset,formation[2]+offset,value)
    return result

"""Algorytm szukania każdej formacji jest identyczny: lecimy od końca i sprawdzamy po kolei
świeczki czy są takie jak formacja nakazuje. Jeśli znajdziemy coś dobrego to kończymy 
(nie interesuje nas co było wcześniej), jeśli nie to zwracamy None"""    

def findDarkCloud(O,C):
    """Znajduje formację zasłony ciemnej chmury - 2-dniowa formacja odwrócenia trendu wzrostowego"""
    if(len(O)<2):        
        return None    
    for i in range(len(O)-1, 1, -1):
        body1=(C[i-1]-O[i-1])/O[i-1]
        body2=(C[i]-O[i])/O[i]                
        if body2 > -LONG_BODY or body1 <LONG_BODY:
            continue        
        if O[i]<=C[i-1]:
            continue
        body1mid=C[i-1]-(C[i-1]-O[i-1])/2
        if(C[i]>=body1mid):
            continue
        return ('dark_cloud',i-1,i)
    return None

def findPiercing(O,C):
    """Znajduje formację przenikania - 2-dniowa formacja odwrócenia trendu spadkowego"""
    if(len(O)<2):        
        return None    
    for i in range(len(O)-1, 1, -1):
        body1=(C[i-1]-O[i-1])/O[i-1]
        body2=(C[i]-O[i])/O[i]
        if body2 < LONG_BODY or body1 > -LONG_BODY:
            continue
        if O[i]>=C[i-1]:
            continue
        body1mid=C[i-1]-(C[i-1]-O[i-1])/2
        if(C[i]<=body1mid):
            continue
        return ('piercing',i-1,i)
    return None    

def findEveningStar(O,C):
    """Znajduje formację gwiazdy wieczornej - 3-dniowa formacja odwrócenia trendu wzrostowego"""
    if(len(O)<3):        
        return None    
    for i in range(len(O)-1, 2, -1):
        body1=(C[i-2]-O[i-2])/O[i-2]
        body2=(C[i-1]-O[i-1])/O[i-1]
        body3=(C[i]-O[i])/O[i]
        if body1 < LONG_BODY or abs(body2) > SHORT_BODY or body3 > -LONG_BODY:
            continue
        if O[i-1]<=C[i-2] or C[i-1]<=C[i-2] or O[i]>=C[i-1]:
            continue
        body1mid=C[i-2]-(C[i-2]-O[i-2])/2
        if(C[i]>=body1mid):
            continue
        return ('evening_star',i-2,i)
    return None    

def findMorningStar(O,C):
    """Znajduje formację gwiazdy porannej - 3-dniowa formacja odwrócenia trendu spadkowego"""
    if(len(O)<3):        
        return None    
    for i in range(len(O)-1, 2, -1):
        body1=(C[i-2]-O[i-2])/O[i-2]
        body2=(C[i-1]-O[i-1])/O[i-1]
        body3=(C[i]-O[i])/O[i]
        if body1 > -LONG_BODY or abs(body2) > SHORT_BODY or body3 < LONG_BODY:
            continue
        if O[i-1]>=C[i-2] or C[i-1]>=C[i-2] or O[i]<=C[i-1]:
            continue
        body1mid=C[i-2]-(C[i-2]-O[i-2])/2
        if(C[i]<=body1mid):
            continue
        return ('morning_star',i-2,i)
    return None    

def findBull3(O,H,L,C):
    """Znajduje formację trójki hossy - 5-dniowa formacja kontynuacji trendu wzrostowego"""
    if(len(O)<5):        
        return None    
    for i in range(len(O)-1, 4, -1):
        body1=(C[i-4]-O[i-4])/O[i-4]
        body2=(C[i-3]-O[i-3])/O[i-3]
        body3=(C[i-2]-O[i-2])/O[i-2]
        body4=(C[i-1]-O[i-1])/O[i-1]
        body5=(C[i]-O[i])/O[i]
        #długości korpusów
        if (body1 < LONG_BODY or abs(body2) > SHORT_BODY or 
            abs(body2) > SHORT_BODY or abs(body2) > SHORT_BODY or body5 < LONG_BODY):
            continue
        #środek porusza się wewnątrz zakresu pierwszej świecy
        if (max(O[i-1],C[i-1])>H[i-4] or max(O[i-2],C[i-2])>H[i-4] or 
            max(O[i-3],C[i-3])>H[i-4] or
            min(O[i-1],C[i-1])<L[i-4] or min(O[i-2],C[i-2])<L[i-4] or 
            min(O[i-3],C[i-3])<L[i-4]):
            continue
        #co najmniej 2 świece w środku czarne
        falls=[x for x in [body2,body3,body4] if x<0]
        if(len(falls)<2):
            continue
        #nowe maksimum na koniec
        if(C[i]<=C[i-4]):
            continue
        return ('bull3',i-4,i)
    return None    

def findBear3(O,H,L,C):
    """Znajduje formację trójki bessy - 5-dniowa formacja kontynuacji trendu spadkowego"""
    if(len(O)<5):        
        return None    
    for i in range(len(O)-1, 4, -1):
        body1=(C[i-4]-O[i-4])/O[i-4]
        body2=(C[i-3]-O[i-3])/O[i-3]
        body3=(C[i-2]-O[i-2])/O[i-2]
        body4=(C[i-1]-O[i-1])/O[i-1]
        body5=(C[i]-O[i])/O[i]
        #długości korpusów
        if (body1 > -LONG_BODY or abs(body2) > SHORT_BODY or 
            abs(body2) > SHORT_BODY or abs(body2) > SHORT_BODY or body5 > -LONG_BODY):
            continue
        #środek porusza się wewnątrz zakresu pierwszej świecy
        if (max(O[i-1],C[i-1])>H[i-4] or max(O[i-2],C[i-2])>H[i-4] or 
            max(O[i-3],C[i-3])>H[i-4] or
            min(O[i-1],C[i-1])<L[i-4] or min(O[i-2],C[i-2])<L[i-4] or 
            min(O[i-3],C[i-3])<L[i-4]):
            continue
        #co najmniej 2 świece w środku białe
        rises=[x for x in [body2,body3,body4] if x>0]
        if(len(rises)<2):
            continue
        #nowe minimum na koniec
        if(C[i]>=C[i-4]):
            continue
        return ('bear3',i-4,i)
    return None    

"""luki traktuję jako osobną rzecz od formacji świecowych 
(podobnie zresztą jak literatura)
po pierwsze nie wymagają świec (wystarczy zwykły wykres słupkowy), 
po drugie kształtują się przez dłuższy czas, więc są IMO ważniejsze"""

def isStraightTrend(array):    
    """Sprawdzamy czy tablica opisuje zdecydowany ruch w górę lub w dół.
    Robimy to wyliczając regresję i sprawdzając czy wszystkie punkty w tablicy 
    są w pasie regresja +/- jakieś sensitivity. Oczywiście sprawdzamy też czy sam trend
    jest odpowiednio silny poprzez badanie współczynnika kierunkowego prostej."""    
    a, b = trendA.regression(array)
    if abs(a) < STRONG_TREND:
        return 0
    for i in range(len(array)):
            y = a*i+b
            if y > (1+STRAIGHT_TREND_VUL)*array[i] or y < (1-STRAIGHT_TREND_VUL)*array[i]:
                    return 0
    return a       

def findGaps(H,L,C):   
    """Szuka luk na fragmentach tablicy o różnej wielkości, zwraca te, które znalazł
    na największym. Zwraca listę par, których pierwszy element to
    lista luk, każda opisana tak jak w findGapsOnFragment, a drugi to wartość."""
    intervals=[(0,1),(1,4),(1,2),(3,4)][-1::-1]
    value=1
    gapsList=[]
    for a,b in intervals:        
        gaps=findGapsOnFragment(H,L,C,a,b)
        if(gaps!=[]):
            gapsList.append((gaps,value))            
        value*=0.75
    return gapsList

def findGapsOnFragment(H,L,C,a,b):
    """Znajduje na danym wycinku wykresu lukę startową, ucieczki i wyczerpania.     
    Interpretacja: Luka startowa - sygnał rozpoczęcia trendu, 
    luka ucieczki - potwierdzenie siły trendu + orientacyjne określenie jego zasięgu (zazwyczaj jest w połowie)
    luka wyczerpania - sygnał że trend się wkrótce skończy    
    Funkcja zwraca listę 0, 1, 2 lub 3 elementową, której
    elementy są krotkami 3-elementowymi: (nazwa, indeks w tablicy, poziom y)"""        
    oldlen=len(C)
    C=C[a*len(C)/b:]
    H=H[a*len(C)/b:]
    L=L[a*len(C)/b:]
    offset=oldlen-len(C)
    trend=isStraightTrend(C)
    if not (len(H)==len(L)==len(C)) or trend==0:
        return []      
    breakaway_gap=None
    continuation_gap=None
    exhaustion_gap=None
    gaps=[]
    amplitude=max(C)-min(C)    
    base=min(C)
    print "straight trend"
    if(trend>0):
        #najpierw szukamy wszystkich luk na wykresie
        for i in range (len(H)-1):
            if(H[i]<L[i+1]):
                #pierwszy element pary to indeks, drugi to wartość (połowa wysokości luki)
                gaps.append( (i,H[i]+(L[i+1]-H[i])/2.) )         
        #teraz szukamy pośród nich luk startu, ucieczki i wyczerpania
        for gap in gaps:
            #luka startowa: możliwie blisko wartości najmniejszej i nie później niż ucieczki lub wyczerpania
            if (((exhaustion_gap==None or gap[0]<exhaustion_gap[0]) and 
                (continuation_gap==None or gap[0]<continuation_gap[0]))
                and (gap[1]-base<LOW_PART*amplitude and breakaway_gap==None or breakaway_gap!=None and gap[1]-base<breakaway_gap[1]-base)):
                breakaway_gap=gap
            #luka ucieczki: możliwie blisko środka, i pomiędzy startową a wyczerpania
            if (((breakaway_gap==None or gap[0]>breakaway_gap[0]) and 
                (exhaustion_gap==None or gap[0]<exhaustion_gap[0]))
                and (LOW_PART*amplitude < gap[1]-base < HIGH_PART*amplitude and continuation_gap==None) 
                or (continuation_gap!=None and abs(gap[1]-base-0.5*amplitude)<abs(continuation_gap[1]-base-0.5*amplitude))):
                continuation_gap=gap
            #luka wyczerpania: możliwie blisko wartości największej ale też nie wcześniej niż ucieczki lub wyczerpania
            if ((breakaway_gap==None or gap[0]>breakaway_gap[0]) and 
                (continuation_gap==None or gap[0]>continuation_gap[0])
                and (gap[1]-base>HIGH_PART*amplitude and exhaustion_gap==None or exhaustion_gap!=None and gap[1]-base>exhaustion_gap[1])):
                exhaustion_gap=gap
        gaps=[]
        if breakaway_gap!=None:
            breakaway_gap=('rising_breakaway_gap',breakaway_gap[0],breakaway_gap[1])
            gaps.append(breakaway_gap)
        if continuation_gap!=None:
            continuation_gap=('rising_continuation_gap',continuation_gap[0],continuation_gap[1])
            gaps.append(continuation_gap)
        if exhaustion_gap!=None:
            exhaustion_gap=('rising_exhaustion_gap',exhaustion_gap[0],exhaustion_gap[1])
            gaps.append(exhaustion_gap)
        return gaps
    #dla trendu malejącego analogicznie, tylko odejmowania i nierówności w drugą stronę
    elif(trend<0):                
        for i in range (len(H)-1):
            if(H[i+1]<L[i]):
                print i, H[i+1], L[i]
                gaps.append( (i+offset,L[i+1]+(H[i]-L[i+1])/2.) )                
        for gap in gaps:
            #luka startowa: możliwie blisko wartości najmniejszej i nie później niż ucieczki lub wyczerpania
            if (((exhaustion_gap==None or gap[0]<exhaustion_gap[0]) and 
                (continuation_gap==None or gap[0]<continuation_gap[0]))
                and (gap[1]-base>HIGH_PART*amplitude and breakaway_gap==None or breakaway_gap!=None and gap[1]>breakaway_gap[1]-base)):
                breakaway_gap=gap
            #luka ucieczki: możliwie blisko środka, i pomiędzy startową a wyczerpania
            if (((breakaway_gap==None or gap[0]>breakaway_gap[0]) and 
                (exhaustion_gap==None or gap[0]<exhaustion_gap[0]))
                and (LOW_PART*amplitude < gap[1]-base < HIGH_PART*amplitude and continuation_gap==None) 
                or (continuation_gap!=None and abs(gap[1]-base-0.5*amplitude)<abs(continuation_gap[1]-base-0.5*amplitude))):
                continuation_gap=gap
            #luka wyczerpania: możliwie blisko wartości największej ale też nie wcześniej niż ucieczki lub wyczerpania
            if ((breakaway_gap==None or gap[0]>breakaway_gap[0]) and 
                (continuation_gap==None or gap[0]>continuation_gap[0])
                and (gap[1]-base<LOW_PART*amplitude and exhaustion_gap==None or exhaustion_gap!=None and gap[1]-base<exhaustion_gap[1])):
                exhaustion_gap=gap
        gaps=[]
        if breakaway_gap!=None:
            breakaway_gap=('falling_breakaway_gap',breakaway_gap[0],breakaway_gap[1])
            gaps.append(breakaway_gap)
        if continuation_gap!=None:
            continuation_gap=('falling_continuation_gap',continuation_gap[0],continuation_gap[1])
            gaps.append(continuation_gap)
        if exhaustion_gap!=None:
            exhaustion_gap=('falling_exhaustion_gap',exhaustion_gap[0],exhaustion_gap[1])
            gaps.append(exhaustion_gap)
        return gaps
    else: 
        return []
