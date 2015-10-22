# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider
import furious
import re, urllib

class iptorrentsFuriousProvider(furious.FuriousProvider):

	ipt_regex = re.compile(r'<a class="t_title" [^>]+>(.*?)</a>.*?href="([^"]*\.torrent)".*?<td.*?<td class=ac>(.*?)</td>.*?<td class="ac t_seeders">(.*?)</td><td class="ac t_leechers">(.*?)</td>', re.MULTILINE)

	def __init__(self, provider):
		furious.FuriousProvider.__init__(self, 'iptorrentsFuriousProvider', provider)

	def authenticate(self):
		resp = self.provider.POST(
			"%s/t"%self.provider.get_setting('url_address'),
			{},
			{},
			"username=%s&password=%s"%(
				self.provider.get_setting('username'),
				self.provider.get_setting('password')
			)
		)

	def searchEpisode(self, episode):
		return self.do(
			"%(imdb_id)s+S%(season)02dE%(episode)02d"%episode,
			self.getTvTags()
		)

	def searchMovie(self, movie):
		return self.do(
			"%(imdb_id)s"%movie,
			self.getMovieTags()
		)

	def parseRawResults(self, data):
		results = []
		for torrent in self.ipt_regex.findall(data):
			url = "%s%s"%(provider.get_setting('url_address'), urllib.quote(torrent[1]))
			results.append({
				'name': torrent[0],
				# 'info_hash': hashlib.sha1(url).hexdigest(),
				'uri': url,
				'seeds': int(torrent[3]),
				'peers': int(torrent[4]),
				'size': furious.human2bytes(torrent[2])
			})

		# print results
		return results

	def do(self, query, tags=[]):
		query_obj = {'q': query}
		for tag in tags:
			query_obj[tag] = ''
		# self.provider.log.info(query_obj)

		resp = self.provider.GET(
			"%s/t"%self.provider.get_setting('url_address'),
			query_obj,
			{}
		)
		if int(resp.code) == 200:
			parsed = self.parseRawResults(resp.data)
			filtered = self.filterPotentials(parsed)
			if self.provider.get_setting('pulsar_integration') == 'magnet':
				results = self.forceMagnets(filtered)
			else:
				results = filtered
			return self.rankResults(results)
		else:
			message = "error request returning %d %s"%(resp.code, resp.msg)
			self.provider.log.error(message)
			self.provider.notify(message)
			return

fp = iptorrentsFuriousProvider(provider)
provider.register(fp.search, fp.searchMovie, fp.searchEpisode)