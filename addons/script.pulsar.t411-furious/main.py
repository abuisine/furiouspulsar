# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider
import urllib
import furious

class t411FuriousProvider(furious.FuriousProvider):

	categories = {
		'Film': 631,
		'Serie TV': 433
	}

	def __init__(self, provider):
		furious.FuriousProvider.__init__(self, 't411FuriousProvider', provider)

	def authenticate(self):
		resp = self.provider.POST(
			"%s/auth"%self.provider.get_setting('url_address'),
			{},
			{},
			"username=%s&password=%s"%(
				self.provider.get_setting('username'),
				self.provider.get_setting('password')
			)
		)
		if int(resp.code) == 200:
			json = resp.json()
			if 'error' in json:
				self.provider.log.info('Authentication error %(code)s: %(error)s'%(json))
				self.provider.notify('Authentication error')
				return
			self.provider.log.info('Got token: %s'%json['token'])
			self.authenticated = True
			self.token = json['token']
			return
		self.provider.log.info('error')
		self.provider.log.info(resp.msg)
		self.provider.notify('Error getting token')
		return

	def searchMovie(self, movie):
		return self.do(urllib.quote(movie['title']), {'cid': self.categories['Film']})

	def searchEpisode(self, episode):
		return self.do(urllib.quote("%(title)s+S%(season)02dE%(episode)02d"%episode), {'cid': self.categories['Serie TV']})

	def search(self, query):
		return self.do(urllib.quote(query))

	def do(self, query, params={}):
		if not self.authenticated:
			return []

		resp = self.provider.GET(
			"%s/torrents/search/%s"%(self.provider.get_setting('url_address'), query),
			params,
			{'Authorization': self.token},
		)

		if int(resp.code) == 200:
			parsed = self.parseJsonResults(resp.json())
			filtered = self.filterPotentials(parsed)
			if self.provider.get_setting('pulsar_integration') == 'magnet':
				results = self.forceMagnets(filtered, headers={'Authorization': self.token})
			else:
				results = filtered
			return self.rankResults(results)
		else:
			message = "error request returning %d %s"%(resp.code, resp.msg)
			self.provider.log.error(message)
			self.provider.notify(message)
			return []

	def parseJsonResults(self, json):
		results = []
		if not 'torrents' in json:
			self.provider.log.info('Error: %s %s'%(json['error_code'], json['error']))
			return []

		for torrent in json['torrents']:
			self.provider.log.info('Getting torrent %s'%torrent['id'])
			results.append({
				"name": torrent['name'],
				"uri": "%s/torrents/download/%s|Authorization=%s"%(self.provider.get_setting('url_address'), torrent['id'], self.token),
				# "uri": "%s/torrents/download/%s"%(self.provider.get_setting('url_address'), torrent['id']),
				# "info_hash": string
				# "trackers": [string, ...]
				"size": int(torrent['size']),
				"seeds": int(torrent['seeders']),
				"peers": int(torrent['leechers']),
				"is_private": True
				# "resolution": int
				# "video_codec": int
				# "audio_codec": int
				# "rip_type": int
				# "scene_rating": int
				# "language": string (ISO 639-1)
			})
		return results

fp = t411FuriousProvider(provider)
provider.register(fp.search, fp.searchMovie, fp.searchEpisode)