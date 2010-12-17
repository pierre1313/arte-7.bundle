VIDEO_PREFIX = "/video/artep7"
MUSIC_PREFIX = "/music/artep7"

VIDEOS_PAGE = 'http://videos.arte.tv/%s/videos'
BASE_ADDRESS = 'http://videos.arte.tv'
SUBCATEGORY = 'http://videos.arte.tv%s,view,rss.xml'
VIDEO_PAGE = 'http://videos.arte.tv/%s/do_delegate/videos/%s,view,asPlayerXml.xml'

NAME = 'Arte+7'

ART   = 'art-default.jpg'
ICON  = 'icon-default.png'
PREFS = 'icon-prefs.png'

####################################################################################################

def Start():

    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, 'Arte+7', ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)
    
    HTTP.CacheTime = 3600

def VideoMainMenu():
    dir = MediaContainer(viewGroup="List")
    mainpage = HTML.ElementFromURL(VIDEOS_PAGE % Prefs['lang'])
    for category in mainpage.xpath('//ul[@id="nav"]/li[not(@class="selected") and not(@class="lastItem")]/a'):  
      dir.Append(Function(DirectoryItem(CategoryParsing,category.text,thumb=R(ICON),art=R(ART)),path = category.get('href')))

    if Prefs['lang'] == 'de':
      dir.Append(PrefsItem(title="Einstellungen",subtile="",summary="Einstellungen",thumb=R(PREFS)))
    elif Prefs['lang'] == 'fr':
   	  dir.Append(PrefsItem(title="Préferences",subtile="",summary="Préferences",thumb=R(PREFS)))
    else:
  	  dir.Append(PrefsItem(title="Preferences",subtile="",summary="Preferences",thumb=R(PREFS)))

    return dir
    
def CategoryParsing(sender,path):
    dir = MediaContainer(viewGroup="List")
    pagetoscrape = HTML.ElementFromURL(BASE_ADDRESS + path)
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
    dir = MediaContainer(viewGroup="InfoList")
    xml = XML.ElementFromURL(VIDEO_PAGE  % (Prefs['lang'],videoid))
    for item in xml.xpath('//videos/video'):
      if item.get('lang') == Prefs['lang']:
        localtitle = title# + ' - ' + item.get('lang')
        link = item.get("ref")
# TO WORK WITH DIRECT LINKS REMOVE THIS SECTION   
        xml = XML.ElementFromURL(link)
        thumb = xml.xpath('//firstThumbnailUrl')[0].text
        path = xml.xpath('//video/url')[0].text
        summary = HTML.ElementFromURL(path).xpath("//div[@class='recentTracksCont']/div/p")[0].text
        subtitle = xml.xpath("//dateVideo")[0].text
        subtitle = subtitle[:subtitle.find('+')-1]
        dir.Append(Function(VideoItem(PlayVideo, title = localtitle, summary = summary, subtitle = subtitle, thumb=thumb),path=path))
#AND USE THIS      
#      dir.Append(Function(DirectoryItem(GetVideos,title = localtitle,summary = summary,thumb=R(ICON),art=R(ART)),title = localtitle,summary = summary,path = link))
    return dir    
    
# TO WORK WITH DIRECT LINKS UNCOMMENT THIS SECTION TOEXPOSE A SUBMENU FOR DIFFERENT QUALITY STREAMS
#def GetVideos(sender,title,summary,path):
#    dir = MediaContainer(viewGroup="List")
#    xml = XML.ElementFromURL(path)
#    thumb = xml.xpath('//firstThumbnailUrl')[0].text
#    localtitle = title
#    link = xml.xpath('//video/url')[0].text
#    summary = HTML.ElementFromURL(link).xpath("//div[@class='recentTracksCont']/div/p")[0].text
#    subtitle = xml.xpath("//dateVideo")[0].text
#    dir.Append(Function(VideoItem(PlayVideo, title = localtitle, summary = summary, subtitle = subtitle, thumb=thumb),path=link))
    #for item in xml.xpath('//urls/url'):
    #  localtitle = title + ' - ' + item.get('quality')
    #  link = item.text#.split("MP4:")
    #  dir.Append(RTMPVideoItem(link, clip = '',width = 640,height = 480, title = localtitle,summary = summary,thumb=thumb))
#    return dir
 
def PlayVideo(sender, path):
	return Redirect(WebVideoItem(path)) 
