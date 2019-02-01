import urllib2
import re
import time
import util

def get_stories(username, password, num):
    url = "http://news.theflyonthewall.com/SERVICE/STORY?NUM=%d&html=true&u=%s&p=%s" % (num, username, password)
    data = urllib2.urlopen(url).read()
    if data[0:6] != '<html>':
        raise Exception("Invalid username/password")

    stories = re.findall("\<script\>.+?\('(?P<story>.+)'\);\</script\>", data)

    now = time.localtime()
    secs = now.tm_hour*3600 + now.tm_min*60 + now.tm_sec
    # Discard if the first story is several hours old (means they're old -- it's a new day)
    if len(stories)>0 and int(stories[0].split("|")[0][1:]) < secs - 3600*6:
        util.info( "First story is from the far past -- shouldn't happen, discarding stories" )
        return []
    
    # Don't return stories if they are far in the future (means they're old -- it's a new day)
    for story in stories:
        if int(story.split("|")[0][1:]) > secs + 3600:
            util.info( "Story is from the far future -- shouldn't happen, discarding stories" )
            return []

    return stories

def test():
    stories = get_stories('bdkearns', 'brazil', 0)
    for story in stories:
        print story
