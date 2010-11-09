# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

VIDEO_PREFIX = "/video/artep7"
MUSIC_PREFIX = "/music/artep7"

VIDEOS_PAGE = 'http://videos.arte.tv/%s/videos'
BASE_ADDRESS = 'http://videos.arte.tv'
SUBCATEGORY = 'http://videos.arte.tv%s,view,rss.xml'
VIDEO_PAGE = 'http://videos.arte.tv/fr/do_delegate/videos/%s,view,asPlayerXml.xml'

NAME = 'Arte+7'

ART           = 'art-default.png'
ICON          = 'icon-default.png'

####################################################################################################

def Start():

    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, 'Arte+7', ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)

def VideoMainMenu():
    dir = MediaContainer(viewGroup="List")
    mainpage = XML.ElementFromURL(VIDEOS_PAGE % 'en',isHTML=True)
    for category in mainpage.xpath('//ul[@id="nav"]/li[not(@class="selected") and not(@class="lastItem")]/a'):  
      dir.Append(Function(DirectoryItem(CategoryParsing,category.text,thumb=R(ICON),art=R(ART)),path = category.get('href')))
    return dir
    
def CategoryParsing(sender,path):
    dir = MediaContainer(viewGroup="List")
    pagetoscrape = XML.ElementFromURL(BASE_ADDRESS + path,isHTML=True)
    for category in pagetoscrape.xpath("//div[@id='listChannel']/ul//a"):
      dir.Append(Function(DirectoryItem(SubCategoryParsing,category.text,thumb=R(ICON),art=R(ART)),path = category.get('href')))
    return dir


def SubCategoryParsing(sender,path):
    dir = MediaContainer(viewGroup="List")
    path = path.replace('/videos','/do_delegate/videos').replace('.html','')
    rss = XML.ElementFromURL(SUBCATEGORY  % path)
    for item in rss.xpath('//item'):
      title = item.xpath("title")[0].text
      summary = item.xpath("description")[0].text
      link = item.xpath("link")[0].text
      videoid = link[link.rfind("/")+1:link.find(".html")]
      dir.Append(Function(DirectoryItem(GetAllVideos,title = title,summary = summary,thumb=R(ICON),art=R(ART)),title = title,summary = summary,videoid = videoid))
    return dir
    
def GetAllVideos(sender,title,summary,videoid):
    dir = MediaContainer(viewGroup="List")
    xml = XML.ElementFromURL(VIDEO_PAGE  % videoid)
    for item in xml.xpath('//videos/video'):
      localtitle = title + ' - ' + item.get('lang')
      link = item.get("ref")
      dir.Append(Function(DirectoryItem(GetVideos,title = localtitle,summary = summary,thumb=R(ICON),art=R(ART)),title = localtitle,summary = summary,path = link))
    return dir    
    
def GetVideos(sender,title,summary,path):
    dir = MediaContainer(viewGroup="List")
    xml = XML.ElementFromURL(path)
    thumb = xml.xpath('//firstThumbnailUrl')[0].text
    for item in xml.xpath('//urls/url'):
      localtitle = title + ' - ' + item.get('quality')
      link = item.text
      dir.Append(RTMPVideoItem(url=link,clip='',width = 640,height = 480, title = localtitle,summary = summary,thumb=thumb))
    return dir
     
