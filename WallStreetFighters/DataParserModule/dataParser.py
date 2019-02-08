# -*- coding: utf-8 -*-
__author__ = "Xai"
__date__ = "$2012-03-02 19:32:01$"

import numpy as np
import re
import csv
import datetime
import urllib2
import cStringIO
import cPickle
import threading

#ZMIENNE GLOBALNE
REMEMBER_COUNT = 15

DATABASE_LAST_UPDATE = datetime.date(2012,3,3)
INDEX_LIST = []
STOCK_LIST = []
FOREX_LIST = []
RESOURCE_LIST = []
BOND_LIST = []
FUTURES_LIST = []
HISTORY_LIST = []
AMEX_HIST = []
NYSE_HIST = []
NASDAQ_HIST = []
UPDATE_FLAG = False


class FinancialObject(object):
	"""Klasa definiująca obiekt finansowy (index,spółkę,surowiec,obligację, etc.), w której przechowywane będą archiwalne notowania i być może obliczone wskaźniki. """
	
	def __init__ (self, name, abbreviation, financialType, dataSource, detail = None,lastUpdate = datetime.date(1971,1,1)):
		self.name = name
		self.abbreviation = abbreviation 
		self.financialType = financialType
		self.dataSource = dataSource
		self.detail = detail #Informacja szczegółowa -> Index - kraj / Społka - index
		self.lastUpdate = lastUpdate #informacja kiedy ostatnio aktualizowane byly dane z archiwum.
		self.currentValue = [] #para wartość i data pobrania
		self.previousValues = []  #lista w wartości z tego samego dnia ale pobranych wcześniej postaci: [datetime, value]
		self.valuesDaily = [] #lista list w przypadku yahoo postaci [[date,open,high,low,close,volume,adj close], [date, ...], ...] 
					# w przypadku Stooq bez adj close.
		self.valuesWeekly = [] # jak wyżej tylko dla danych tygodniowych
		self.valuesMonthly = [] # jak wyżej tylko dla danych miesięcznych
		self.dailyUpdate = datetime.date(1971,1,1)
		self.monthlyUpdate = datetime.date(1971,1,1)
		self.weeklyUpdate = datetime.date(1971,1,1)

	def getCurrentValue(self):
		
		global UPDATE_FLAG
		UPDATE_FLAG = True	

		"""Metoda aktualizująca dane dotyczące aktualnej wartości obiektu oraz przenosząca poprzednią wartość do listy poprzednich wartości"""
		if self.dataSource == "Yahoo":
			tmpObj = createWithCurrentValueFromYahoo(self.name, self.abbreviation, self.financialType, self.detail)
		elif self.dataSource == "Stooq":
			tmpObj = createWithCurrentValueFromStooq(self.name, self.abbreviation, self.financialType, self.detail)
		self.previousValues = self.previousValues + self.currentValue
		self.currentValue = tmpObj.currentValue

	def updateArchive(self, timePeriod):
		"""Metoda aktualizująca dane istniejącego obiektu. Tworzy nowy tymczasowy obiekt i kopiuje jego zawartość do obiektu 'self'. """
		day = datetime.timedelta(days=1)
		lastUpdate = self.lastUpdate + day		

		global UPDATE_FLAG
		try:
		
			if self.dataSource == "Yahoo":
				if timePeriod == 'daily' and self.dailyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					self.dailyUpdate = datetime.date.today()
					if self.valuesDaily == []: 
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesDaily[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesDaily[0][0]+day
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)		
					self.valuesDaily = self.valuesDaily + tmpObj.valuesDaily
					self.dailyUpdate = tmpObj.dailyUpdate
				elif timePeriod == 'weekly' and self.weeklyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					self.weeklyUpdate = datetime.date.today()	
					if self.valuesWeekly == []: 
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesWeekly[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesWeekly[0][0]+day
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)		
					self.valuesWeekly = self.valuesWeekly + tmpObj.valuesWeekly
					self.weeklyUpdate = tmpObj.weeklyUpdate
				elif timePeriod == 'monthly' and self.monthlyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					self.monthlyUpdate = datetime.date.today()
					if self.valuesMonthly == []: 
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesMonthly[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesMonthly[0][0]+day
						tmpObj = createWithArchivesFromYahoo(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)		
					self.valuesMonthly= self.valuesMonthly + tmpObj.valuesMonthly
					self.monthlyUpdate = tmpObj.monthlyUpdate
			elif self.dataSource == "Stooq":
				if timePeriod == 'daily' and self.dailyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					if self.valuesDaily == []: 
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesDaily[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesDaily[0][0]+day
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)		
					self.valuesDaily = self.valuesDaily + tmpObj.valuesDaily
					self.dailyUpdate = tmpObj.dailyUpdate
				elif timePeriod == 'weekly' and self.weeklyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					if self.valuesWeekly == []: 
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesWeekly[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesWeekly[0][0]+day
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)		
					self.valuesWeekly = self.valuesWeekly + tmpObj.valuesWeekly
					self.weeklyUpdate = tmpObj.weeklyUpdate
				elif timePeriod == 'monthly' and self.monthlyUpdate != datetime.date.today():
					UPDATE_FLAG = True
					if self.valuesMonthly == []: 
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod)	
					elif self.valuesMonthly[0][0] == datetime.date.today():
						return
					else:
						date = self.valuesMonthly[0][0]+day
						tmpObj = createWithArchivesFromStooq(self.name, self.abbreviation, self.financialType, self.detail, timePeriod, date)				
					self.valuesMonthly= self.valuesMonthly + tmpObj.valuesMonthly
					self.monthlyUpdate = tmpObj.monthlyUpdate
		except DataAPIException:
			UPDATE_FLAG = True
			return

	def getArray(self, time):
		"""Funkcja zwracająca rekordowaną tablicę (numpy.recarray) dla informacji w odstępie czasu przekazanym jako parametr funkcji. Pozwala to dostać się do poszczególnych tablic używając odpowiednich rekordów: 'date' 'open' etc."""
		if self.financialType == 'forex' or self.financialType == 'bond' or self.financialType == 'resource' or self.financialType == 'future':
			tmplist = []
			if time == 'daily':
				for x in self.valuesDaily:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],0))
			if time == 'weekly':
				for x in self.valuesWeekly:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],0))
			if time == 'monthly':
				for x in self.valuesMonthly:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],0))
			return np.array(tmplist,dtype = [('date','S10'),('open',float),('high',float),('low',float),('close',float),('volume',float)])
		else:
			tmplist = []
			if time == 'daily':
				for x in self.valuesDaily:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],x[5]))
			if time == 'weekly':
				for x in self.valuesWeekly:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],x[5]))
			if time == 'monthly':
				for x in self.valuesMonthly:
					tmplist.append((str(x[0]),x[1],x[2],x[3],x[4],x[5]))
			return np.array(tmplist,dtype = [('date','S10'),('open',float),('high',float),('low',float),('close',float),('volume',float)])
			
	def getIndex(self, begin, end, time = 'daily'):
		"""Funkcja zwracająca indeksy tablicy dla danego przedziału czasu"""
		if begin > end:
			return
		if time == 'daily':
			if end < self.valuesDaily[0][0]:
				raise DataAPIException('Stock was not noted yet ')
			size = len(self.valuesDaily)
			
			if begin < self.valuesDaily[0][0]:
				start = 1
			else:
				start = 0
				while (begin > self.valuesDaily[start][0]):
					start += 1
			
			if end > self.valuesDaily[size-1][0]:
				finish = size-2
			else:
				finish = start
				while (end > self.valuesDaily[finish][0]):
					finish += 1
			return [start-1,finish+1]
		if time == 'weekly':
			size = len(self.valuesWeekly)
			if end < self.valuesWeekly[0][0]:
				raise DataAPIException('Stock was not noted yet ')
			if begin < self.valuesWeekly[0][0]:
				start = 1
			else:
				start = 0
				while (begin > self.valuesWeekly[start][0]):
					start += 1
		
			if end > self.valuesWeekly[size-1][0]:
				finish = size-2
			else:
				finish = start
				while (end > self.valuesWeekly[finish][0]):
					finish += 1
			return [start-1,finish+1]
		if time == 'monthly':
			size = len(self.valuesMonthly)
			if end < self.valuesMonthly[0][0]:
				raise DataAPIException('Stock was not noted yet ')
			if begin < self.valuesMonthly[0][0]:
				start = 1
			else:
				start = 0
				while (begin > self.valuesMonthly[start][0]):
					start += 1
			
			if end > self.valuesMonthly[size-1][0]:
				finish = size-2
			else:
				finish = start
				while (end > self.valuesMonthly[finish][0]):
					finish += 1
			return [start-1,finish+1]
#koniec definicji klasy

class DataAPIException(Exception):
	def __init__(self,value):
		self.value = value
	def __str__(self):
		return repr(self.value)

def createWithCurrentValueFromYahoo(name, abbreviation, financialType, detail):
	"""Funkcja tworząca obiekt zawierający aktualną na daną chwilę wartość ze strony finance.yahoo"""
	
	"""
	global HISTORY_LIST
	global UPDATE_FLAG
	if UPDATE_FLAG == False:
		finObj = isInHistory(abbreviation)
		if finObj != None:
			finObj.getCurrentValue()
			return finObj
	"""

	finObj = FinancialObject(name,abbreviation, financialType, "Yahoo", detail)

	url = "http://finance.yahoo.com/q?s="+abbreviation
	try:
		site = urllib2.urlopen(url)
		print url
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException('Connection Error!')
	pageSource = site.read()
	if abbreviation[0] == '^':
		pattern = '\\'+abbreviation.lower()+'">([0-9]*,*[0-9]+\.*[0-9]+)<'
	else:	
		pattern = abbreviation.lower()+'">([0-9]*,*[0-9]+\.*[0-9]+)<'
	pattern = re.compile(pattern)
	m = re.search(pattern,pageSource)
	
	timeNow = datetime.datetime.now()

	pattern = 'Bid:</th>.*?>([0-9.]+)</span><small> x <.*?>([0-9]+)</span></sma.*?Ask:</th>.*?>([0-9.]+)</span><small> x <.*?>([0-9]+)'
	pattern = re.compile(pattern)
	
	
	finObj.currentValue = [float(m.group(1).replace(',','')),timeNow]
	m = re.search(pattern,pageSource)

	"""
	if UPDATE_FLAG == False:
		if len(HISTORY_LIST) == REMEMBER_COUNT:
			HISTORY_LIST[1:REMEMBER_COUNT:1]=HISTORY_LIST[0:REMEMBER_COUNT-1:1]
			HISTORY_LIST[0] = finObj
		else:
			HISTORY_LIST = [finObj] + HISTORY_LIST
	UPDATE_FLAG = False	
	"""
	return finObj

def createWithCurrentValueFromStooq(name, abbreviation, financialType, detail):
	"""Funkcja tworząca obiekt zawierający aktualną na daną chwilę wartość ze strony Stooq.pl"""
	"""
	global HISTORY_LIST
	global UPDATE_FLAG
	if UPDATE_FLAG == False:
		finObj = isInHistory(abbreviation)
		if finObj != None:
			finObj.getCurrentValue()
			return finObj
	"""

	finObj = FinancialObject(name,abbreviation, financialType, "Stooq", detail)
	
	url = "http://stooq.pl/q/?s="+abbreviation.lower()
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException('Connection Error!')
	pageSource = site.read()
	pattern = '_c[0-9]>([0-9]*,*[0-9]+\.*[0-9]+)<'
	pattern = re.compile(pattern)
	m = re.search(pattern,pageSource)
	timeNow = datetime.datetime.now()
	finObj.currentValue = [float(m.group(1).replace(',','')),timeNow]
	pattern = '>Bid<.*?>([0-9.]*)</span></font>.*?>x([0-9.mgk]*)</span></font>.*?>Ask<.*?>([0-9.mgk]*)</span>.*?>x([0-9.mgk]*)</span>.*?Wolumen<br>.*?>([0-9.mgk]*)</span>.*?>Obrót<br>.*?>([0-9.mgk]*)</.*?>Transakcje<br><.*?>([0-9.mgk]*)<'
	pattern = re.compile(pattern)
	m = re.search(pattern,pageSource)

	"""
	if UPDATE_FLAG == False:
		if len(HISTORY_LIST) == REMEMBER_COUNT:
			HISTORY_LIST[1:REMEMBER_COUNT:1]=HISTORY_LIST[0:REMEMBER_COUNT-1:1]
			HISTORY_LIST[0] = finObj
		else:
			HISTORY_LIST = [finObj] + HISTORY_LIST
	UPDATE_FLAG = False	
	"""
	return finObj

def createWithArchivesFromYahoo(name, abbreviation, financialType, detail, timePeriod, sinceDate = datetime.date(1971,1,1)):
	"""Funkcja tworząca obiekt zawierający archiwalne dane pobrane ze strony finance.yahoo dotyczące obiektu zdefiniowanego w parametrach funkcji"""
	
	global HISTORY_LIST
	global UPDATE_FLAG
	if UPDATE_FLAG == False:
		print isInHistory(abbreviation)
		finObj = isInHistory(abbreviation)
		if finObj != None:
			finObj.updateArchive(timePeriod)
			return finObj

	currentDate = datetime.date.today()

	finObj = FinancialObject(name,abbreviation, financialType, "Yahoo", detail, currentDate)
	print "Pobieram: " + abbreviation
	url = 'http://ichart.finance.yahoo.com/table.csv?s='+abbreviation+'&a='+str(sinceDate.month-1)+'&b='+str(sinceDate.day)	 
        url = url+'&c='+str(sinceDate.year)+'&d='+str(currentDate.month-1)+'&e='
	url = url+str(currentDate.day)+'&f='+str(currentDate.year)+'&g=d&ignore=.csv'
	if timePeriod == 'weekly':
		url = url.replace('&g=d', '&g=w')
	elif timePeriod == 'monthly':
		url = url.replace('&g=d', '&g=m')
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException('Connection Error!')
	csvString = site.read()
	csvString = cStringIO.StringIO(csvString)
	dataCsv = csv.reader(csvString)
	dataCsv.next()

	if timePeriod == 'daily':
		finObj.dailyUpdate = datetime.date.today()
		for row in dataCsv:
			dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4]),int(row[5])]]
			finObj.valuesDaily = dataRow + finObj.valuesDaily
	elif timePeriod == 'weekly':
		finObj.weeklyUpdate = datetime.date.today()	
		for row in dataCsv:
			dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4]),int(row[5])]]
			finObj.valuesWeekly = dataRow + finObj.valuesWeekly 
	elif timePeriod == 'monthly':
		finObj.monthlyUpdate = datetime.date.today()
		for row in dataCsv:
			dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4]),int(row[5])]]
			finObj.valuesMonthly = dataRow + finObj.valuesMonthly
	if UPDATE_FLAG == False:
		if len(HISTORY_LIST) == REMEMBER_COUNT:
			HISTORY_LIST[1:REMEMBER_COUNT:1]=HISTORY_LIST[0:REMEMBER_COUNT-1:1]
			HISTORY_LIST[0] = finObj
		else:
			HISTORY_LIST += [finObj]
	UPDATE_FLAG = False	
	return finObj 

def createWithArchivesFromStooq(name, abbreviation, financialType, detail, timePeriod, sinceDate = datetime.date(1971,1,1)):
	"""Funkcja tworząca obiekt zawierający aktualną na daną chwilę wartość ze strony stooq.pl"""

	global HISTORY_LIST
	global UPDATE_FLAG
	if UPDATE_FLAG == False:
		finObj = isInHistory(abbreviation)
		if finObj != None:
			finObj.updateArchive(timePeriod)
			return finObj

	finObj = FinancialObject(name,abbreviation, financialType, "Stooq", detail)
	currentDate = datetime.date.today()

	try:
		url= 'http://stooq.pl/q/d/?s='+abbreviation.lower()
		opener = urllib2.build_opener()
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		site = opener.open(url)
		x = site.info()['Set-Cookie']
		opener = urllib2.build_opener()
		opener.addheaders = [('User-agent', 'Mozilla/5.0'), ('Referer','http://stooq.pl/q/d/?s=08n'),('Host','stooq.p')]
		opener.addheaders = [('Cookie', x)]
		url2 = 'http://stooq.pl/q/d/l/?s='+abbreviation.lower()+'&d1='+parserDateToString(sinceDate)+'&d2='
		url2 = url2 + parserDateToString(currentDate)+'&i=d'
		if timePeriod == 'weekly':
			url2 = url2.replace('&i=d', '&i=w')
		elif timePeriod == 'monthly':
			url2 = url2.replace('&i=d', '&i=m')
		site = opener.open(url2)

	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException('Connection Error!')
	csvString = site.read()
	csvString = cStringIO.StringIO(csvString)
	dataCsv = csv.reader(csvString)
	dataCsv.next()
	if timePeriod == 'daily':
		for row in dataCsv:
			try:
				if financialType == 'forex' or financialType == 'bond' or financialType == 'resource':
					dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4])]]
				else:
					date = parserStringToDate(row[0])
					dataRow=[[date,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5])]]
				finObj.valuesDaily = finObj.valuesDaily + dataRow
			except IndexError, ex:
				pass
	elif timePeriod == 'weekly':
		for row in dataCsv:
			if financialType == 'forex' or financialType == 'bond' or financialType == 'resource':
				dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4])]]
			else:
				date = parserStringToDate(row[0])
				dataRow = [[date,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5])]]	
			finObj.valuesWeekly = finObj.valuesWeekly + dataRow
	elif timePeriod == 'monthly':
		for row in dataCsv:	
			if financialType == 'forex' or financialType == 'bond' or financialType == 'resource':
				dataRow = [[parserStringToDate(row[0]),float(row[1]),float(row[2]),float(row[3]),float(row[4])]]
			else:
				date = parserStringToDate(row[0])
				dataRow = [[date,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5])]]	
			finObj.valuesMonthly = finObj.valuesMonthly + dataRow
	if UPDATE_FLAG == False:
		if len(HISTORY_LIST) == REMEMBER_COUNT:
			HISTORY_LIST[1:REMEMBER_COUNT:1]=HISTORY_LIST[0:REMEMBER_COUNT-1:1]
			HISTORY_LIST[0] = finObj
		else:
			HISTORY_LIST = [finObj] + HISTORY_LIST
	UPDATE_FLAG = False	
	return finObj
	
	 
def parserStringToDate(string):
	"""Funkcja zmieniająca ciąg znaków postaci "YYYY-MM-DD" na obiekt klasy datatime.date"""
	string = string.split('-')
	x = datetime.date(int(string[0]),int(string[1]),int(string[2]))
	return x

def parserDateToString(date):
	"""Funkcja zmieniająca obiekt datetime.date na string postaci YYYYMMDD"""
	date = str(date)
	date = date.replace('-','')
	return date

def updateDatabase():
	"""Funkcja sprawdzająca czy na rynkach pojawiły się nowe spółki, jeśli tak to dodaje spółki do bazy danych. """
	global DATABASE_LAST_UPDATE	
	current = datetime.datetime.today()
	csvFile  = open('data2.wsf', "ab")
	dmonth = datetime.timedelta(days=30)
	while(DATABASE_LAST_UPDATE.month <= current.month and DATABASE_LAST_UPDATE.month <= current.year):

		smonth = DATABASE_LAST_UPDATE.ctime()[4:7:1]
		syear = DATABASE_LAST_UPDATE.year%100
		url = "http://biz.yahoo.com/ipo/prc_"+smonth.lower()+str(syear)+".html"
		try:
			site = urllib2.urlopen(url)
		except urllib2.URLError, ex:
			print "Something wrong happend! Check your internet connection!"
			raise DataAPIException('Connection Error!')
		pageSource = site.read()
		pattern = '(?s)Prev(.*)Prev'
		pattern = re.compile(pattern)
		m = re.search(pattern,pageSource)
		pageSource = m.group(0)

		pattern = '>([0-9][0-9]*-[A-Z][a-z][a-z]-[0-9][0-9])</td><td>(.*)</td><td.*>([A-Z][A-Z][A-Z]*)<.*>M<'
		for m in re.finditer(pattern,pageSource):
			if isInStock(m.group(3)) == None:
				print m.group(3)+m.group(2)+m.group(1)
				csvFile.write(m.group(3)+','+m.group(2)+',Yahoo,NYSE\n')
		DATABASE_LAST_UPDATE = DATABASE_LAST_UPDATE + dmonth
			

def loadData():
	"""Funkcja wczytująca dane z 'bazy danych' na temat dostępnych do wyszukania obiektów finansowych i zapisuje je do zmiennych globalnych""" 
	global INDEX_LIST
	global STOCK_LIST
	global FOREX_LIST
	global RESOURCE_LIST
	global BOND_LIST
	global FUTURES_LIST
	global DATABASE_LAST_UPDATE
	global HISTORY_LIST
	global AMEX_HIST
	global NASDAQ_HIST
	global NYSE_HIST
	csvFile  = open('data1.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	dataCsv.next()
	for row in dataCsv:
		INDEX_LIST = INDEX_LIST + [[row[0],row[1],row[2],'America']]
	csvFile  = open('data2.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	flag = True
	for row in dataCsv:
		if flag == True:
			DATABASE_LAST_UPDATE = parserStringToDate(row[1])
			flag = False
		else:	
			STOCK_LIST.append([row[0],row[1],row[2],row[3]])
	
	csvFile  = open('data3.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	dataCsv.next()
	for row in dataCsv:
		FOREX_LIST = FOREX_LIST + [[row[0],row[1],row[2],row[3]]]
	csvFile  = open('data4.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	dataCsv.next()
	for row in dataCsv:
		RESOURCE_LIST = RESOURCE_LIST + [[row[0],row[1],row[2],row[3]]]
	csvFile  = open('data5.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	dataCsv.next()
	for row in dataCsv:
		BOND_LIST = BOND_LIST + [[row[0],row[1],row[2],row[3]]]	
	csvFile  = open('data6.wsf', "rb")
	dataCsv = csv.reader(csvFile)
	dataCsv.next()
	for row in dataCsv:
		FUTURES_LIST = FUTURES_LIST + [[row[0],row[1],row[2],row[3]]]	
	csvFile  = open('AMEX.csv', "rb")
	dataCsv = csv.reader(csvFile)
	for row in dataCsv:
		AMEX_HIST += [[parserStringToDate(row[0][0:4:1]+'-'+row[0][4:6:1]+'-'+row[0][6:8:1]),row[1],row[2],row[3],row[4],row[5],row[6]]]
	csvFile  = open('NASDAQ.csv', "rb")
	dataCsv = csv.reader(csvFile)
	for row in dataCsv:
		NASDAQ_HIST += [[parserStringToDate(row[0][0:4:1]+'-'+row[0][4:6:1]+'-'+row[0][6:8:1]),row[1],row[2],row[3],row[4],row[5],row[6]]]
	csvFile  = open('NYSE.csv', "rb")
	dataCsv = csv.reader(csvFile)
	for row in dataCsv:
		NYSE_HIST += [[parserStringToDate(row[0][0:4:1]+'-'+row[0][4:6:1]+'-'+row[0][6:8:1]),row[1],row[2],row[3],row[4],row[5],row[6]]]
	#loadHistory()


def getAdvDec(date):
	"""Funkcja dopisująca do bazy danych informacje o spadkach/wzrostach z bazy danych"""
	list = []
	url = 'http://unicorn.us.com/advdec/'+ str(date.year)+'/adU'+ parserDateToString(date) +'.txt'
	try:
		site = urllib2.urlopen(url)
	except urllib2.HTTPError, ex:
		if ex.code == 404:
			print "Nie można pobrać danych. Rynki mogłybyć nie czynne w tym dniu."
			raise DataAPIException('Connection Error!')
		return
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException('Connection Error!')
	pageSource = site.read()
	pageSource = pageSource.replace(' ','')
	csvString = cStringIO.StringIO(pageSource)
	dataCsv = csv.reader(csvString)
	dataCsv.next()
	dataCsv.next()
 	i = 0
	for row in dataCsv:
		if i == 0:
			csvFile  = open('NYSE.csv', "ab")
		elif i == 1:
			csvFile  = open('AMEX.csv', "ab")
		elif i == 2:
			csvFile  = open('NASDAQ.csv',"ab")
		csvFile.write(parserDateToString(date)+','+row[1]+','+row[2]+','+row[3]+','+row[4]+','+row[5]+','+row[6]+'\n')
		i+=1

def updateAdvDec():
	size = len(AMEX_HIST)
	last_date = AMEX_HIST[size-1][0]
	day = datetime.timedelta(days=1)
	if last_date + day == datetime.date.today():
		return
	else:	
		now = last_date + day
		while now != datetime.date.today():
			getAdvDec(now)
			now+=day

def getAdvDecInPeriodOfTime(begin,end,index):
	tmplist = []
	day = datetime.timedelta(days=1)
	if index == 'NYSE':
		for row in NYSE_HIST:
			if row[0] >= begin and row[0] <= end:
				tmplist +=  [(str(row[0]),row[1],row[2],row[3],row[4],row[5],row[6])]
		return np.array(tmplist,dtype = [('date','S10'),('adv',int),('dec',int),('unc',int),('advv',int),('decv',int),('uncv',int)])
	if index == 'AMEX':
		for row in AMEX_HIST:
			if row[0] >= begin and row[0] <= end:
				tmplist +=  [(str(row[0]),row[1],row[2],row[3],row[4],row[5],row[6])]
		return np.array(tmplist,dtype = [('date','S10'),('adv',int),('dec',int),('unc',int),('advv',int),('decv',int),('uncv',int)])
	if index == 'NASDAQ':
		for row in NASDAQ_HIST:
			if row[0] >= begin and row[0] <= end:
				tmplist +=  [(str(row[0]),row[1],row[2],row[3],row[4],row[5],row[6])]
		return np.array(tmplist,dtype = [('date','S10'),('adv',int),('dec',int),('unc',int),('advv',int),('decv',int),('uncv',int)])


def isInHistory(abbreviation):
	"""Funkcja sprawdzająca czy obiekt finansowy o podanym skrócie znajduje się w historii"""
	for x in HISTORY_LIST:
		if x.abbreviation == abbreviation:
			return x	
	return None

def isInStock(abbreviation):
	"""Funkcja sprawdzająca czy obiekt finansowy o podanym skrócie znajduje się w historii"""
	for x in STOCK_LIST:
		if x[0] == abbreviation and x[2] == 'Yahoo':
			return x	
	return None

def saveHistory(file):
	"""Funkcja zapisująca bierzącą historie w pliku"""
	global HISTORY_LIST
	print "zapisalem"
	for x in HISTORY_LIST:
		print x.abbreviation
	cPickle.dump(HISTORY_LIST, file)

class loadHistory(threading.Thread):
	"""Funkcja zapisująca bierzącą historie w pliku"""
    	def __init__(self, File):
        	threading.Thread.__init__(self)
		self.file = File

	def run(self):
		global HISTORY_LIST
		HISTORY_LIST = cPickle.load(self.file)
		self.file.close()

def top5Volume():
	"""Funkcja zwracajaca listę 5 spółek o najwyższym wolumenie"""
	TOP_VOLUME = []
	url = "http://finance.yahoo.com/actives?e=us"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()
	#pattern = '[A-Z]+">([A-Z]+)</a></b>.*?> ([0-9,]+)</span></td>'
	pattern = '[A-Z]+">([A-Z]+)</a></b>.*?([0-9.]*)</span></b>.*?"color:(.*?);.*?>([0-9.]*)<.*?> \(([0-9.]*%)\)</b>'
	pattern = re.compile(pattern)
	i = 0
	for m in re.finditer(pattern,pageSource):
		if i < 5:
			if m.group(3) == '#cc0000':
				TOP_VOLUME.append([m.group(1),m.group(2),'-' + m.group(4), '-' + m.group(5)])
				i += 1
			else:
				TOP_VOLUME.append([m.group(1),m.group(2),m.group(4),m.group(5)])
				i += 1
	return TOP_VOLUME

def top5Gainers():
	"""Funkcja zwracajaca listę 5 spółek o najwiekszym wzroscie"""
	TOP_GAINERS = []
	url = "http://finance.yahoo.com/gainers?e=us"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()
	pattern = '[A-Z]+">([A-Z]+)</a></b>.*?([0-9.]*)</span></b>.*?;">([0-9.]*)<.*?> \(([0-9.]*%)\)</b>'
	pattern = re.compile(pattern)
	i = 0
	for m in re.finditer(pattern,pageSource):
		if i < 5:
			TOP_GAINERS.append([m.group(1),m.group(2),m.group(3),m.group(4)])
			i += 1
	return TOP_GAINERS

def top5Losers():
	"""Funkcja zwracajaca listę 5 spółek o najwiekszym spadku"""
	TOP_LOSERS = []
	url = "http://finance.yahoo.com/losers?e=us"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()
	pattern = '[A-Z]+">([A-Z]+)</a></b>.*?([0-9.]*)</span></b>.*?;">([0-9.]*)<.*?> \(([0-9.]*%)\)</b>'
	pattern = re.compile(pattern)
	i = 0
	for m in re.finditer(pattern,pageSource):
		if i < 5:
			TOP_LOSERS.append([m.group(1),m.group(2),'-' + m.group(3),'-' + m.group(4)])
			i += 1
	return TOP_LOSERS

def getMostPopular():
	"""Funkcja zwracająca aktualne wartości najbardziej popularnych obiektów"""
	mostPopular = []
	
	url = "http://finance.yahoo.com/marketupdate/overview?u"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()	
	
	mostPopular.append(mostPopularIndicesSearch('Dow', pageSource))
	mostPopular.append(mostPopularIndicesSearch('Nasdaq', pageSource))
	mostPopular.append(mostPopularIndicesSearch('S&amp;P 500', pageSource))

	url = "http://finance.yahoo.com/"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()

	mostPopular.append(mostPopularPatternSearch('EUR/USD',pageSource))
	mostPopular.append(mostPopularPatternSearch('10-Year',pageSource))
	mostPopular.append(mostPopularPatternSearch('Gold',pageSource))
	mostPopular.append(mostPopularPatternSearch('Oil',pageSource))

	mostPopular[2][0] = 'S&P 500' 
	return mostPopular


def mostPopularPatternSearch(keyWord,source):

	pattern = '">' + keyWord + '<.*?">([0-9,.]*)<.*?>([0-9,.+-]*)<\/span.*?>([0-9.+-]*%)<'
	pattern = re.compile(pattern, re.DOTALL)
	m = re.search(pattern,source)
	return [keyWord,m.group(1),m.group(2),m.group(3)]

def mostPopularIndicesSearch(keyWord,pageSource):
	
	pattern = '">' + keyWord + '<.*?">([0-9,.]*)<\/span>.*?"color:(.*?);.*?>([0-9,.]*)<.*?> \(([0-9.]*%)\)<'
	pattern = re.compile(pattern, re.DOTALL)
	m = re.search(pattern,pageSource)
	if m.group(2) == '#cc0000':
		return [keyWord,m.group(1),'-' + m.group(3),'-' + m.group(4)]
	else:
		return [keyWord,m.group(1),'+' + m.group(3),'+' + m.group(4)]

def getMostPopularCurrencies():
	""" """
	
	url = "http://finance.yahoo.com/"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()
	
	mostPopular = []
	mostPopular.append(mostPopularPatternSearch('EUR/USD',pageSource))
	mostPopular.append(mostPopularPatternSearch('USD/JPY',pageSource))
	mostPopular.append(mostPopularPatternSearch('GBP/USD',pageSource))

	return mostPopular

def getMostPopularCommodities():
	""" """
	
	url = "http://finance.yahoo.com/"
	try:
		site = urllib2.urlopen(url)
	except urllib2.URLError, ex:
		print "Something wrong happend! Check your internet connection!"
		raise DataAPIException("Connection ERROR!")
	pageSource = site.read()
	
	mostPopular = []
	mostPopular.append(mostPopularPatternSearch('Gold',pageSource))
	mostPopular.append(mostPopularPatternSearch('Silver',pageSource))
	mostPopular.append(mostPopularPatternSearch('Copper',pageSource))
	
	return mostPopular

def getDataToLightWeightChart(abbreviation, financialType, source):
	global UPDATE_FLAG
	today = datetime.date.today()
	ddays = datetime.timedelta(days=30)
	since = today - ddays
	UPDATE_FLAG = True
	if source == "Stooq":
		finObj = createWithArchivesFromStooq("", abbreviation, financialType, "", "daily", since)
	else:
	   	finObj = createWithArchivesFromYahoo("", abbreviation, financialType, "", "daily", since)
	UPDATE_FLAG = False
	return finObj
	




########################################################################################################

