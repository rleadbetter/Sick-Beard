# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import datetime
import os
import sys
import re
import urllib2

import sickbeard

from sickbeard import helpers, classes, logger, db, exceptions

from sickbeard.common import Quality, MULTI_EP_RESULT, SEASON_RESULT
from sickbeard import tvcache
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from lib.hachoir_parser import createParser

from sickbeard.name_parser.parser import InvalidNameException
from sickbeard.completparser import CompleteParser

class GenericProvider:

    NZB = "nzb"
    TORRENT = "torrent"

    def __init__(self, name):

        # these need to be set in the subclass
        self.providerType = None
        self.name = name
        self.url = ''

        self.supportsBacklog = False
        self.supportsAbsoluteNumbering = False

        self.cache = tvcache.TVCache(self)

    def getID(self):
        return GenericProvider.makeID(self.name)

    @staticmethod
    def makeID(name):
        return re.sub("[^\w\d_]", "_", name).lower()

    def imageName(self):
        return self.getID() + '.gif'

    def _checkAuth(self):
        return

    def isActive(self):
        if self.providerType == GenericProvider.NZB and sickbeard.USE_NZBS:
            return self.isEnabled()
        elif self.providerType == GenericProvider.TORRENT and sickbeard.USE_TORRENTS:
            return self.isEnabled()
        else:
            return False

    def isEnabled(self):
        """
        This should be overridden and should return the config setting eg. sickbeard.MYPROVIDER
        """
        return False

    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """

        if self.providerType == GenericProvider.NZB:
            result = classes.NZBSearchResult(episodes)
        elif self.providerType == GenericProvider.TORRENT:
            result = classes.TorrentSearchResult(episodes)
        else:
            result = classes.SearchResult(episodes)

        result.provider = self

        return result


    def getURL(self, url, headers=None):
        """
        By default this is just a simple urlopen call but this method should be overridden
        for providers with special URL requirements (like cookies)
        """

        if not headers:
            headers = []

        result = None

        try:
            result = helpers.getURL(url, headers)
        except (urllib2.HTTPError, IOError), e:
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None

        return result
    
    def get_episode_search_strings(self,ep_obj):
        return self._get_episode_search_strings(ep_obj)
    
    def downloadResult(self, result):
        """
        Save the result to disk.
        """

        logger.log(u"Downloading a result from " + self.name+" at " + result.url)

        data = self.getURL(result.url)

        if data == None:
            return False

        # use the appropriate watch folder
        if self.providerType == GenericProvider.NZB:
            saveDir = sickbeard.NZB_DIR
            writeMode = 'w'
        elif self.providerType == GenericProvider.TORRENT:
            saveDir = sickbeard.TORRENT_DIR
            writeMode = 'wb'
        else:
            return False

        # use the result name as the filename
        fileName = ek.ek(os.path.join, saveDir, helpers.sanitizeFileName(result.name) + '.' + self.providerType)

        logger.log(u"Saving to " + fileName, logger.DEBUG)

        try:
            fileOut = open(fileName, writeMode)
            fileOut.write(data)
            fileOut.close()
            helpers.chmodAsParent(fileName)
        except IOError, e:
            logger.log("Unable to save the file: "+ex(e), logger.ERROR)
            return False

        # as long as it's a valid download then consider it a successful snatch
        return self._verify_download(fileName)

    def _verify_download(self, file_name=None):
        """
        Checks the saved file to see if it was actually valid, if not then consider the download a failure.
        Returns a Boolean
        """
        
        logger.log(u"Verifying Download %s" % file_name, logger.DEBUG)
        try:
            with open(file_name, "rb") as f:
                magic = f.read(16)
                if self.is_valid_torrent_data(magic):
                    return True
                else:
                    logger.log("Magic number for %s is neither 'd8:announce' nor 'd12:_info_length', got '%s' instead" % (file_name, magic), logger.WARNING)
                    #logger.log(f.read())
                    return False
        except Exception, eparser:
            logger.log("Failed to read magic numbers from file: "+ex(eparser), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            return False

    @classmethod
    def is_valid_torrent_data(cls, torrent_file_contents):
        # According to /usr/share/file/magic/archive, the magic number for
        # torrent files is 
        #    d8:announce
        # So instead of messing with buggy parsers (as was done here before)
        # we just check for this magic instead.
        # Note that a significant minority of torrents have a not-so-magic of "d12:_info_length",
        # which while not explicit in the spec is valid bencode and works with Transmission and uTorrent.
        return torrent_file_contents is not None and \
            (torrent_file_contents.startswith("d8:announce") or \
             torrent_file_contents.startswith("d12:_info_length"))

    def searchRSS(self):
        self.cache.updateCache()
        return self.cache.findNeededEpisodes()

    def getQuality(self, item, anime=False):
        """
        Figures out the quality of the given RSS item node
        
        item: An xml.dom.minidom.Node representing the <item> tag of the RSS feed
        
        Returns a Quality value obtained from the node's data 
        """
        (title, url) = self._get_title_and_url(item) #@UnusedVariable
        logger.log(u"geting quality for:" + title+ " anime: "+str(anime),logger.DEBUG)
        quality = Quality.nameQuality(title, anime)
        return quality
    
    def _doSearch(self, show=None):
        return []

    def _get_season_search_strings(self, show, season, episode=None):
        return []

    def _get_episode_search_strings(self, ep_obj):
        return []
    
    def _get_title_and_url(self, item):
        """
        Retrieves the title and URL data from the item XML node

        item: An xml.dom.minidom.Node representing the <item> tag of the RSS feed

        Returns: A tuple containing two strings representing title and URL respectively
        """

        """we are here in the search provider it is ok to delete the /.
        i am doing this because some show get posted with a / in the name
        and during qulaity check it is reduced to the base name
        """
        title = helpers.get_xml_text(item.getElementsByTagName('title')[0]).replace("/"," ")
        try:
            url = helpers.get_xml_text(item.getElementsByTagName('link')[0])
            if url:
                url = url.replace('&amp;','&')
        except IndexError:
            url = None
        
        return (title, url)
    
    def findEpisode (self, episode, manualSearch=False, searchString=None):

        self._checkAuth()
        if searchString:
            logger.log(u"Searching "+self.name+" for '" + ek.ek(str, searchString) + "'")
        else:
            logger.log(u"Searching "+self.name+" for episode " + episode.prettyName(True))

        self.cache.updateCache()
        results = self.cache.searchCache(episode, manualSearch)
        logger.log(u"Cache results: "+str(results), logger.DEBUG)

        # if we got some results then use them no matter what.
        # OR
        # return anyway unless we're doing a manual search
        if results or not manualSearch:
            return results

        if searchString: # if we already got a searchstring don't bother make one
            search_strings = [searchString]
        else:
            search_strings = self._get_episode_search_strings(episode)

        itemList = []
        for cur_search_string in search_strings:
            itemList += self._doSearch(cur_search_string, show=episode.show)


        for item in itemList:

            (title, url) = self._get_title_and_url(item)

            cp = CompleteParser(show=episode.show, tvdbActiveLookUp=True)
            cpr = cp.parse(title)

            parse_result = cpr.parse_result

            if episode.show.air_by_date:
                if parse_result.air_date != episode.airdate:
                    logger.log("Episode " + title + " didn't air on " + str(episode.airdate) + ", skipping it", logger.DEBUG)
                    continue
            elif cpr.season != episode.season or episode.episode not in cpr.episodes:
                logger.log("Episode " + title + " isn't " + str(episode.scene_season) + "x" + str(episode.scene_episode) + " (beware of scene conversion) , skipping it", logger.DEBUG)
                continue

            if not episode.show.wantEpisode(episode.season, episode.episode, cpr.quality, manualSearch):
                logger.log(u"Ignoring result " + title + " because we don't want an episode that is " + Quality.qualityStrings[cpr.quality], logger.DEBUG)
                continue

            logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

            result = self.getResult([episode])
            result.url = url
            result.name = title
            result.quality = cpr.quality
            result.release_group = parse_result.release_group
            result.is_proper = cpr.is_proper

            results.append(result)

        return results



    def findSeasonResults(self, show, season, scene=False):

        itemList = []
        results = {}

        for curString in self._get_season_search_strings(show, season, scene):
            itemList += self._doSearch(curString, show=show)

        for item in itemList:

            (title, url) = self._get_title_and_url(item)
            # parse the file name
            cp = CompleteParser(show=show)
            cpr = cp.parse(title)
            if not cpr:
                continue

            # make sure we want the episode
            wantEp = True
            for epNo in cpr.episodes:
                if not show.wantEpisode(cpr.season, epNo, cpr.quality):
                    wantEp = False
                    break

            if not wantEp:
                logger.log(u"Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[cpr.quality], logger.DEBUG)
                continue

            logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

            # make a result object
            epObj = []
            for curEp in cpr.episodes:
                epObj.append(show.getEpisode(cpr.season, curEp))

            result = self.getResult(epObj)
            result.url = url
            result.name = title
            result.quality = cpr.quality
            result.release_group = cpr.release_group
            result.is_proper = cpr.is_proper

            if len(epObj) == 1:
                epNum = epObj[0].episode
            elif len(epObj) > 1:
                epNum = MULTI_EP_RESULT
                logger.log(u"Separating multi-episode result to check for later - result contains episodes: " + str(cpr.episodes), logger.DEBUG)
            elif len(epObj) == 0:
                epNum = SEASON_RESULT
                result.extraInfo = [show]
                logger.log(u"Separating full season result to check for later", logger.DEBUG)

            if epNum in results:
                results[epNum].append(result)
            else:
                results[epNum] = [result]

        return results

    def findPropers(self, date=None):

        results = self.cache.listPropers(date)

        return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]


    # Dictionary of blacklisted torrent urls.  Keys are the url, values are the 
    # timestamp when it was added
    url_blacklist = {}

    # How long does an entry stay in the URL_BLACKLIST?
    URL_BLACKLIST_EXPIRY_SECS = 172800 # 172800 = 2 days
    
    @classmethod
    def urlIsBlacklisted(cls, url):
        """
        Check if a url is blacklisted.  
        @param url: (string)
        @return: bool 
        """
        if url is None:
            return False
        if url.startswith('http://extratorrent.com/') or url.startswith('https://extratorrent.com/'):
            # This site is permanently blacklisted (no direct torrent links, just ads)
            return True
        if url in cls.url_blacklist:
            if time.time() - cls.url_blacklist[url] < cls.URL_BLACKLIST_EXPIRY_SECS:
                # still blacklisted
                return True
            else:
                # no longer blacklisted, remove it from the list
                del cls.url_blacklist[url]
        return False
    
    @classmethod
    def blacklistUrl(cls, url):
        """
        Add a url to the blacklist.  It stays there for URL_BLACKLIST_EXPIRY_SECS.
        @param url: (string) 
        """
        if url is not None: 
            cls.url_blacklist[url] = time.time()


class NZBProvider(GenericProvider):

    def __init__(self, name):

        GenericProvider.__init__(self, name)

        self.providerType = GenericProvider.NZB

class TorrentProvider(GenericProvider):

    def __init__(self, name):

        GenericProvider.__init__(self, name)

        self.providerType = GenericProvider.TORRENT
