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



import urllib
import datetime
import time

from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard import classes, show_name_helpers, helpers

from sickbeard import exceptions, logger, db
from sickbeard.common import *
from sickbeard import tvcache
from lib.dateutil.parser import parse as parseDate

class NyaaProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "Nyaa")

        self.supportsBacklog = True
        self.description = u"Nyaa Anime torrents."
        self.supportsAbsoluteNumbering = True

        self.cache = NyaaCache(self)

        self.url = 'http://www.nyaa.eu/'

    def isEnabled(self):
        return sickbeard.NYAA
    
    def imageName(self):
        return 'nyaa.png'

    def _get_season_search_strings(self, show, season, scene=False):
        names = []
        if season is -1:
            names = [show.name.encode('utf-8')]
        names.extend(show_name_helpers.makeSceneSeasonSearchString(show, season, scene=scene))
        return names

    def _get_episode_search_strings(self, ep_obj):
        # names = [(ep_obj.show.name + " " + str(ep_obj.absolute_number)).encode('utf-8')]
        names = show_name_helpers.makeSceneSearchString(ep_obj)
        return names

    def _doSearch(self, search_string, show=None):
        if show and not show.is_anime:
            logger.log(u"" + str(show.name) + " is not an anime skiping " + str(self.name))
            return []

        params = {
            "cats": "1_37",     #eng. translated anime
            "term": search_string.encode('utf-8')            
        }

        searchURL = self.url + "?page=rss&" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        searchResult = self.getURL(searchURL)

        # Pause to avoid 503's
        time.sleep(5)

        if searchResult == None:
            return []

        try:
            parsedXML = parseString(searchResult)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load NYAA RSS feed: " + str(e).decode('utf-8'), logger.ERROR)
            return []

        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)

            if not title or not url:
                logger.log(u"The XML returned from the NYAA RSS feed is incomplete, this result is unusable: " + searchResult, logger.ERROR)
                continue

            url = url.replace('&amp;', '&')

            results.append(curItem)

        return results

class NyaaCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll Nyaa every 20 minutes max        
        self.minTime = 20

    def _getRSSData(self):
        url = self.provider.url + '?page=rss&'
        urlArgs = {"cats": "1_37".encode('utf-8')}

        url += urllib.urlencode(urlArgs)

        logger.log(u"NYAA cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NyaaProvider()
