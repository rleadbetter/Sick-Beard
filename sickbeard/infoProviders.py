# Author: Dennis Lutter <lad1337@gmail.com>
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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import sickbeard
from sickbeard import helpers, logger

class InfoInterface(dict):

    id = None
    name = None
    
    def  __init__(self,interfaceType="tvdb",settings={}):
        
        self.inteface = None
        if interfaceType == "tvdb":
            self.inteface = TvDBInterface(settings)
        elif interfaceType == "tvrage":
            self.inteface = TvRageInterface(settings)
        elif interfaceType == "anidb":
            self.inteface = AnidbInterface(settings)
        
        if not self.inteface:
            raise UnkownInterfaceType()
        self.interfaceType = interfaceType
        logger.log(u"New interface created with type "+self.interfaceType)

    def __getitem__(self,key):
        
        logger.log(u""+self.interfaceType+" interface got request for: "+str(key))
        return self.inteface[key]


class GenericInfoInterface(object):
    """
       generic info interface 
    """
    shows = {}
    
    def __init__(self,settings):
        """
            override this by subclass
        """
        pass
    
    def __getitem__(self,key):
        """
            override this by subclass
        """
        return None
        

class TvDBInterface(GenericInfoInterface):
    """
        TheTvDB interface
        this will provide a interface to the thetvdb and use the tvdb_api for this
        Warning: we are cheating. we are suposed to map the tvdb_api to the internal structure but we directly map to the tvdb_api
        beacuse the internal is defined by the tvdb_api
    """
    from lib.tvdb_api import tvdb_api, tvdb_exceptions
    
    def __init__(self,settings):        
        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        for setting in settings:
            ltvdb_api_parms[setting] = settings[setting]

        self.link = self.tvdb_api.Tvdb(**ltvdb_api_parms)

    def __getitem__(self, key):
        return self.link[key]


class TvRageInterface(GenericInfoInterface):
    pass

class AnidbInterface(GenericInfoInterface):
    """
        AniDb.net interface
        this will provide a interface to anidb and use the adba libary for this
    """
    import lib.adba as adba
    
    def __init__(self,settings):
        self.link = self._make_connection(self)
        pass
    
    def _make_connection(self):
        """
        if not helpers.set_up_anidb_connection():
            raise
        """
        return sickbeard.ADBA_CONNECTION
     
    def __getitem__(self, key):
        """Handles tvdb_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._getShowData(key)
            return self.shows[key]
        
        key = key.lower() # make key lower case
        sid = self._nameToSid(key)
        return self.shows[sid]
    
    def _nameToSid(self,name):
        anime = self.adba.Anime(self.link, name)
        show = self._create_abstract_show(anime)
        self.shows[anime.aid] = show
        
        return show["sid"]
    
    def _getShowData(self,aid):
        anime = self.adba.Anime(self.link, aid)
        show = self._create_abstract_show(anime)
        self.shows[anime.aid] = show
        
    
    def _create_abstract_show(self,anime):
        """
            will map every available fields from a adba abstract anime to a Abstract show
        """
        show = AbstractShow()
        # TODO: make general if possible otherwise expand
        show["sid"] = anime.aid
        show[anime.aid]["seriesname"] = anime.name
        
        return show
        
        

"""
the folowing "abstract" classes a basicly a copy of the classes found in the tvdb_api
they porpose is to give a common datastructure for all info providers (subclasses of GenericInfoInterface)
the tvdb_api data structure was choosen because sb was build to use it and it does seam generic enough
"""


class AbstractShow(dict):
    """
        this will behave very much the way the show obj behaves we get from tvdb_api
        the GenericShowInfoInterface subclasses should provide as a mapper
        it is GenericShowInfoInterface subclass duty to provide a suficend data mapping
    """
    
    def __init__(self):
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        return "<Show %s (containing %s seasons)>" % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)

        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if isinstance(key, int) or key.isdigit():
            # Episode number x was not found
            raise AbstractTVObjectSeasonNotFound("Could not find season %s" % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise AbstractTVObjectAttributeNotFound("Cannot find attribute %s" % (repr(key)))
        
        
    def airedOn(self, date):
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise AbstractTVObjectEpisodeNotFound("Could not find any episodes that aired on %s" % date)
        return ret

    def search(self, term = None, key = None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)

        Always returns an array (can be empty). First index contains the first
        match, and so on.

        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrieve the episode name of the
        first match.

        Search terms are converted to lower case (unicode) strings.

        # Examples
        
        These examples assume t is an instance of Tvdb():
        
        >>> t = Tvdb()
        >>>

        To search for all episodes of Scrubs with a bit of data
        containing "my first day":

        >>> t['Scrubs'].search("my first day")
        [<Episode 01x01 - My First Day>]
        >>>

        Search for "My Name Is Earl" episode named "Faked His Own Death":

        >>> t['My Name Is Earl'].search('Faked His Own Death', key = 'episodename')
        [<Episode 01x04 - Faked His Own Death>]
        >>>

        To search Scrubs for all episodes with "mentor" in the episode name:

        >>> t['scrubs'].search('mentor', key = 'episodename')
        [<Episode 01x02 - My Mentor>, <Episode 03x15 - My Tormented Mentor>]
        >>>

        # Using search results

        >>> results = t['Scrubs'].search("my first")
        >>> print results[0]['episodename']
        My First Day
        >>> for x in results: print x['episodename']
        My First Day
        My First Step
        My First Kill
        >>>
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term = term, key = key)
            if len(searchresult) != 0:
                results.extend(searchresult)
        #end for cur_season
        return results

class AbstractSeason(dict):
    def __repr__(self):
        return "<Season instance (containing %s episodes)>" % (
            len(self.keys())
        )

    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise AbstractTVObjectEpisodeNotFound("Could not find episode %s" % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term = None, key = None):
        """Search all episodes in season, returns a list of matching Episode
        instances.

        >>> t = Tvdb()
        >>> t['scrubs'][1].search('first day')
        [<Episode 01x01 - My First Day>]
        >>>

        See Show.search documentation for further information on search
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term = term, key = key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results


class AbstractEpisode(dict):
    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return "<Episode %02dx%02d - %s>" % (seasno, epno, epname)
        else:
            return "<Episode %02dx%02d>" % (seasno, epno)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise AbstractTVObjectAttributeNotFound("Cannot find attribute %s" % (repr(key)))

    def search(self, term = None, key = None):
        """Search episode data for term, if it matches, return the Episode (self).
        The key parameter can be used to limit the search to a specific element,
        for example, episodename.
        
        This primarily for use use by Show.search and Season.search. See
        Show.search for further information on search

        Simple example:

        >>> e = Episode()
        >>> e['episodename'] = "An Example"
        >>> e.search("examp")
        <Episode 00x00 - An Example>
        >>>

        Limiting by key:

        >>> e.search("examp", key = "episodename")
        <Episode 00x00 - An Example>
        >>>
        """
        if term == None:
            raise TypeError("must supply string to search for (contents)")

        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find( unicode(term).lower() ) > -1:
                return self
            #end if cur_value.find()
        #end for cur_key, cur_value


class AbstractActors(list):
    """Holds all Actor instances for a show
    """
    pass


class AbstractActor(dict):
    """Represents a single actor. Should contain..

    id,
    image,
    name,
    role,
    sortorder
    """
    def __repr__(self):
        return "<Actor \"%s\">" % (self.get("name"))


"""
Errors
"""
class UnkownInterfaceType(Exception):
    "An unkown interface type was given"
    
class AbstractTVObjectSeasonNotFound():
    "Could not find season"
    
class AbstractTVObjectAttributeNotFound():
    "Cannot find attribute"
    
class AbstractTVObjectEpisodeNotFound():
    "Cannot find attribute"
    
