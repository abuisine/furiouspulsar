# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider
import furious

class rarbgFuriousProvider(furious.FuriousProvider):

	app_id = 'script.pulsar.rarbg-furious'

	def __init__(self, provider):
		furious.FuriousProvider.__init__(self, 'rarbgFuriousProvider', provider)

	def authenticate(self):
		resp = self.provider.GET(provider.get_setting('url_address'),
			{
				'get_token': 'get_token',
				'app_id': self.app_id
			}
		)
		if int(resp.code) == 200:
			json = resp.json()
			self.authenticated = True
			self.token = json['token']
			self.provider.log.info('Got token: %s'%json['token'])
			return
		else:
			provider.log.info('error getting token: %s'%resp.msg)
			provider.notify('Error getting token')
			return

	def searchEpisode(self, episode):
		return self.do(self.addCategories(
			{
				'token': self.token,
				'app_id': self.app_id,
				'mode': 'search',
				'sort': 'seeders',
				'format': 'json_extended',
				'search_imdb': "%(imdb_id)s"%episode,
				'search_string': "S%(season)02dE%(episode)02d"%episode
			},
			self.getTvTags()
		))

	def searchMovie(self, movie):
		return self.do(self.addCategories(
			{
				'token': self.token,
				'app_id': self.app_id,
				'mode': 'search',
				'sort': 'seeders',
				'format': 'json_extended',
				'search_imdb': "%(imdb_id)s"%movie
			},
			self.getMovieTags()
		))

	def do(self, query):
		if not self.authenticated:
			return []

		resp = self.provider.GET(self.provider.get_setting('url_address'), query)

		if int(resp.code) == 200:
			parsed = self.parseJsonResults(resp.json())
			filtered = self.filterPotentials(parsed)
			return self.rankResults(filtered)
		else:
			return []

	def addCategories(self, params, tags):
		categories = ""
		for tag in tags:
			if categories == "":
				categories = tag
			else:
				categories += ';%s'%tag
		if categories != "":
			params['category'] = categories
		return params

	def parseJsonResults(self, json):
		results = []
		if 'torrent_results' in json:
			torrents = json['torrent_results']
			for torrent in torrents:
				results.append({
					"name": torrent['title'],
					"uri": torrent['download'],
					# "info_hash": string
					# "trackers": [string, ...]
					"size": torrent['size'],
					"seeds": torrent['seeders'],
					"peers": torrent['leechers']
					# "resolution": int
					# "video_codec": int
					# "audio_codec": int
					# "rip_type": int
					# "scene_rating": int
					# "language": string (ISO 639-1)
				})
			return results
		else:
			self.provider.log.info('Error: %d %s'%(json['error_code'], json['error']))
			return results




fp = rarbgFuriousProvider(provider)
provider.register(fp.search, fp.searchMovie, fp.searchEpisode)