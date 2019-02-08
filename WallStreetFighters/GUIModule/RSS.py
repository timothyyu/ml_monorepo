#! /usr/bin/env python

import urllib2
from xml.dom import minidom, Node


class RSSItem:
	def __init__(self,title="",description="", link="",pubDate = ""):
                self.title = title
		self.description = description
		self.link = link
		self.pubDate = pubDate

class RSSReader:
	
	name = ""
	def __init__(self,RSSUrl):
		"""Initialize the class"""
		self.RSSUrl = RSSUrl;
		try:
                        self.xmldoc = self.GetXMLDocument(RSSUrl)
                except  (IOError, OSError):
                        self.xmldoc = None
                if not self.xmldoc == None:
                        for itemNode in self.xmldoc.documentElement.childNodes:
                                if (itemNode.nodeName == "channel"):
                                        self.name = self.GetChildText(itemNode,"title")
		
	def GetXMLDocument(self,RSSUrl):
		"""This function reads in a RSS URL and then returns the XML documentn on success"""
		urlInfo = urllib2.urlopen(RSSUrl)
		xmldoc = None
		if (urlInfo):
			xmldoc = minidom.parse(urlInfo)
		else:
			print "Error Getting URL"
		
		return xmldoc
	
	def GetItemText(self,xmlNode):
		"""Get the text from an xml item"""
		text = ""
		for textNode in xmlNode.childNodes:
			if (textNode.nodeType == Node.TEXT_NODE):
				text += textNode.nodeValue
		return text
	
	def GetChildText(self, xmlNode, childName):
		"""Get a child node from the xml node"""
		if (not xmlNode):
			print "Error GetChildNode: No xml_node"
			return ""
		for itemNode in xmlNode.childNodes:
			if (itemNode.nodeName==childName):
				return self.GetItemText(itemNode)
		"""Return Nothing"""
		return ""
	
	def CreateRSSItem(self,itemNode):

		"""Create an RSS item and return it"""
		title = '# '
		title += self.GetChildText(itemNode,"title")
		description = self.GetChildText(itemNode,"description")
		link = self.GetChildText(itemNode, "link")
		pubDate = self.GetChildText(itemNode, "pubDate")
		return RSSItem(title,description,link,pubDate)
	
	def GetItems(self):
		"""Generator to get items"""
		print("ddd")
                if not self.xmldoc == None:
                        for itemNode in self.xmldoc.documentElement.childNodes:
                                for itemNode in itemNode.childNodes:
                                        if (itemNode.nodeName == "item"):
                                                """Allright we have an item"""
                                                rssItem = self.CreateRSSItem(itemNode)
                                                yield rssItem       
