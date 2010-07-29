from PMS import Plugin, Log, XML, HTTP, Utils
from PMS.MediaXML import *
from PMS.FileTypes import PLS
from PMS.Shorthand import _L, _R, _E, _D
import re
import pickle
import base64

from FrameworkAdditions import *

####################################################################################################
MYVERSION = "0.7"
#0.3: ignore labels and descriptions that can't be converted to utf-8
#0.4: ignore missing description pages and video files (access outside arte regions)
#0.5: wmv is directly referenced in the page, skip parsing .asx
#0.6: Make language structure consistent, Add title2
#0.7: Parse asx again (Plex does no stream handling since 0.8.2), cache asx only five minutes

PLUGIN_PREFIX     = "/video/artep7"

SHORT_CACHE_INTERVAL        = 300 #five minutes
CACHE_INTERVAL              = 1800 #half hour
LONG_CACHE_INTERVAL         = 604800 #one week
DEBUG                       = False

VIDEOS_DATE = "Datum"
VIDEOS_T7 = "Top7"

URL_BASE = "http://plus7.arte.tv"
#URLs were determined from noscript section of welcome page
URL_TOP = "streaming-home/1698112,templateId=renderCarouselHTML,CmPage=1697480,filter=top7,CmPart=com.arte-tv.streaming.html"
URL_ALL = "streaming-home/1698112,templateId=renderCarouselHTML,CmPage=1697480,CmPart=com.arte-tv.streaming.html"
#the tag-cloud portion of the date-overview
URL_DATES = "streaming-home/1698112,templateId=renderTagCloud,CmPage=1697480,filter=dates,CmPart=com.arte-tv.streaming.html"
URL_DATE = "streaming-home/1698112,templateId=renderCarouselHTML,CmPage=1697480,selectedTags=%s,CmPart=com.arte-tv.streaming.html"

SELECTED_TAGS = "selectedTags="

####################################################################################################

def Start():
  Plugin.AddRequestHandler(PLUGIN_PREFIX, HandleRequest, _L("arte+7"), "icon-default.png", "art-default.png")
  Plugin.AddViewGroup("Menu", viewMode="InfoList", contentType="items")

  
####################################################################################################

def HandleRequest(pathNouns, count):
  
  dir = MenuContainer()
  if count == 0:
    return GetTopMenu()
    
  if count == 1:
    if GetTypePart(pathNouns[0]) == VIDEOS_T7:
      return GetMenuTopSeven(GetLangPart(pathNouns[0]))
    if GetTypePart(pathNouns[0]) == VIDEOS_DATE:
      return GetMenuDate(GetLangPart(pathNouns[0]))
  
  if count == 2 and GetTypePart(pathNouns[0]) == VIDEOS_DATE:
    return GetMenuSpecificDate(GetLangPart(pathNouns[0]), pathNouns[1])

  return dir.ToXML()

####################################################################################################
# Returns a plugin path with language
def GetPluginPath():
    return PLUGIN_PREFIX + "/"
    
####################################################################################################
# Returns a prefix for a url with language
def GetArtePath(lang):
    return URL_BASE + "/" + lang + "/"
    
####################################################################################################
# Returns the top level menu
def GetTopMenu():
  dir = MenuContainer()
  dir.AppendItem(DirectoryItem(GetPluginPath() + "de" + VIDEOS_T7, "Top 7 (Deutsch)"))
  dir.AppendItem(DirectoryItem(GetPluginPath() + "de" + VIDEOS_DATE, "Datum (Deutsch)"))
  dir.AppendItem(DirectoryItem(GetPluginPath() + "fr" + VIDEOS_T7, "Top 7 (Francais)"))
  dir.AppendItem(DirectoryItem(GetPluginPath() + "fr" + VIDEOS_DATE, "Dates (Francais)"))
  
  return dir.ToXML()

####################################################################################################
# Returns the language specific label for "date"
def GetDateLabel(lang):
  if (lang == "de"):
    return "Datum"
  else:
    return "Dates"

####################################################################################################
# Returns the language part of the top level menu
def GetLangPart(url):
  return url[0:2];

####################################################################################################
# Returns the type part of the top level menu
def GetTypePart(url):
  return url[2:len(url)];

####################################################################################################
# Returns the top level menu
def GetMenuTopSeven(lang):  
  dir = MenuContainer(title2="Top 7") 
  AddEntriesFromListPage(GetArtePath(lang) + URL_TOP, dir)
    
  return dir.ToXML()

####################################################################################################
# Returns the menu displaying all video entries available
def GetMenuAll(lang):
  dir = MenuContainer()
  AddEntriesFromListPage(GetArtePath(lang) + URL_ALL, dir)
  return dir.ToXML()

####################################################################################################
# Returns the menu with video items for a specific date
def GetMenuSpecificDate(lang, tag):
  dir = MenuContainer(title2=GetSpecificDateLabel(lang, tag))
  dateUrl = GetArtePath(lang) + URL_DATE%(tag,)
  #Add entries for this date
  AddEntriesFromListPage(dateUrl, dir)
  return dir.ToXML()

####################################################################################################
# Returns the menu with the list of available dates
def GetMenuDate(lang):
  dir = MenuContainer(title2=GetDateLabel(lang))
  site = XMLElementFromURL(GetArtePath(lang) + URL_DATES, True, CACHE_INTERVAL)  
  
  entryObjs = site.xpath('//span/a')
  numEntries = len(entryObjs)
  for entry in range(0,numEntries):
    entryObj = entryObjs[entry]
    url = entryObj.xpath('@href')[0]
    selectedTag = GetSelectedTag(url)
    name = entryObj.text
    dir.AppendItem(DirectoryItem(GetPluginPath() + lang + VIDEOS_DATE + "/" + selectedTag, name))

  return dir.ToXML()

####################################################################################################
# Returns the date label to a specific date-tag
def GetSpecificDateLabel(lang, tag):
  site = XMLElementFromURL(GetArtePath(lang) + URL_DATES, True, CACHE_INTERVAL)  

  entryObjs = site.xpath('//span/a')
  numEntries = len(entryObjs)
  for entry in range(0,numEntries):
    entryObj = entryObjs[entry]
    url = entryObj.xpath('@href')[0]
    selectedTag = GetSelectedTag(url)
    name = entryObj.text
    if (selectedTag == tag):
      return name;
  return GetDateLabel(lang)
####################################################################################################
# Returns from a url the query parameter for selectedTags
def GetSelectedTag(url):
    pos = url.find(SELECTED_TAGS)
    if (pos > -1):
        endPos = url.find(".", pos)
        if (endPos > -1):
            return url[pos+len(SELECTED_TAGS):endPos]
    return ""

####################################################################################################
# Parses the list page and puts all found videos into the dir object
def AddEntriesFromListPage(pageUrl, dir):
  site = XMLElementFromURL(pageUrl, True, CACHE_INTERVAL)  

  entryObjs = site.xpath('//li')
  numEntries = len(entryObjs)
  for entry in range(0,numEntries):
    entryObj = entryObjs[entry]
    detailUrl = entryObj.xpath('a/@href')[0]
    name = entryObj.xpath('a')[0].text
    thumbUrl = entryObj.xpath('img/@src')[0]
    
    try:
        #for reading video url and description we have to parse each video's page
        detailPage = XMLElementFromURL(detailUrl, True, LONG_CACHE_INTERVAL) 
        desc = detailPage.xpath('//p[@class="headline"]')[0].text
        #if there is only a short description then the complete description is in p[@class="text"]
        if len(desc.rstrip()) == 0:
          desc = detailPage.xpath('//p[@class="text"]')[0].text
        #read the length from the info-area
        subtitle = GetInfo(detailPage)
        #convert name and description to provide correct unicode characters (thanks marcoppc)
        name=Utf8Decode(name, "name", detailUrl)
        desc=Utf8Decode(desc, "desc", detailUrl)
        subtitle=Utf8Decode(subtitle, "subtitle", detailUrl)

        #for determining the video url we need to parse the javascript that prepares the player
        javascript = detailPage.xpath('//div[@id="content"]/script')[0].text
        videoUrl = ParseVideoJavascript(javascript, 'HQ')
        #if no high quality found then use medium quality (some streams are not available in HQ)
        if len(videoUrl) == 0:
          Log.Add("No HQ video file, trying MQ in " + detailUrl)
          videoUrl = ParseVideoJavascript(javascript, 'MQ')
        #the video url contains an xml page that references the stream itself
        if len(videoUrl) > 0:
          #if (videoUrl.endswith(".asx")):
              #asx, further parsing needed
              Log.Add("Video url used as asx: " + videoUrl)
              videoStreamUrl = ParseVideoUrl(videoUrl)
              if len(videoStreamUrl) > 0:
                #Log.Add("Adding video: " + name)
                vidItem = VideoItem(videoStreamUrl, name, desc, "", thumbUrl)
                vidItem.SetAttr("subtitle", subtitle)
                dir.AppendItem(vidItem)
              else:
                Log.Add("Error: No video stream found in " + videoUrl)      
          #else:
          #    #wmv referenced directly, put it into the videoItem
          #    vidItem = VideoItem(videoUrl, name, desc, "", thumbUrl)
          #    vidItem.SetAttr("subtitle", subtitle)
          #    dir.AppendItem(vidItem)   
        else:
          Log.Add("Error: No video file found in " + detailUrl)
    except:
        #we skip this video entry, there was an error reading the detail page
        Log.Add("Error " + sys.exc_info()[0] + " reading detail page " + detailUrl)
  return dir 
####################################################################################################
# decodes utf-8
def Utf8Decode(source, textType, url):
    try:
        return source.encode("iso-8859-1").decode("utf-8")
    except:
        Log.Add("Error: could not decode " + textType + " for url " + url)
        return ""
####################################################################################################
# parses the info region and returns length and year
def GetInfo(detailPage):
    infoArea = detailPage.xpath('//p[@class="info"]')[0].text
    startPos = infoArea.find('(')
    if (startPos > -1):
      endPos = infoArea.find(')', startPos+1)
      if (endPos > -1):
        return infoArea[startPos:endPos+1]
    return ""

####################################################################################################
# parses the xml video file (asx)
def ParseVideoUrl(videoUrl):
  videoPage = HTTP.GetCached(videoUrl, SHORT_CACHE_INTERVAL)
  href = GetValue(videoPage, "HREF")
  return href

####################################################################################################
# parses the javascript that contains the video urls
def ParseVideoJavascript(js, requestedQuality):
    #there are at most four entries, if less then the rest is always empty string
    for entry in range(0,4):
        format = GetValue(js, 'availableFormats[%d]["format"]' % (entry,))
        quality = GetValue(js, 'availableFormats[%d]["quality"]' % (entry,))
        url = GetValue(js, 'availableFormats[%d]["url"]' % (entry,))
        #return "arte+7: js entries - " + format + "," + quality + ":" + url
        if (format == 'WMV' and quality == requestedQuality):
            return url
    return ""

####################################################################################################
# parses a string for a value assignment (string in quotes after the specified name)  
def GetValue(source, name):
    pos = source.find(name)
    if (pos > -1):
        pos = pos + len(name)
        startPos = source.find('"', pos+1)
        if (startPos > -1):
            endPos = source.find('"', startPos+1)
            if (endPos > -1):
                return source[startPos+1:endPos]
    return ""
    
####################################################################################################

# FRAMEWORK ADDITIONS:

# The below is borrowed from The Escapist plugin

class MenuContainer(MediaContainer):
  def __init__(self, art="art-default.png", viewGroup="Menu", title1=None, title2=None, noHistory=False, replaceParent=False):
    if title1 is None:
      title1 = _L("nvl")
    MediaContainer.__init__(self, art, viewGroup, title1, title2, noHistory, replaceParent)


