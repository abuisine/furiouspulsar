# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider, addon
import re, bencode, hashlib, urllib

movie_regex = re.compile(r'<a class="t_title" [^>]+>(.*?)</a>.*?href="([^"]*\.torrent)".*?<td.*?<td class=ac>(.*?)</td>.*?<td class="ac t_seeders">(.*?)</td><td class="ac t_leechers">(.*?)</td>', re.MULTILINE)
hash_regex = re.compile(r'/download\.php/([^/]+)/')

def parseTorrent(data):
	results = []
	decoded_torrent = bencode.bdecode(data)
	decoded_info = decoded_torrent['info']
	encoded_info = bencode.bencode(decoded_info)
	sha1 = hashlib.sha1(encoded_info).hexdigest()
	results.append("xt=urn:btih:"+sha1)

	if "name" in decoded_info:
		results.append("dn="+urllib.quote(decoded_info["name"], safe=""))

	trackers = []
	if "announce-list" in decoded_torrent:
		for urllist in decoded_torrent["announce-list"]:
			trackers += urllist
	elif "announce" in decoded_torrent:
		trackers.append(decoded_torrent["announce"])

	for tracker in trackers:
		results.append("tr=%s"%urllib.quote(tracker, safe=""))

	return {
		'info_hash': sha1,
		'name': decoded_info["name"],
		'trackers': trackers,
		'magnet': "magnet:?%s"%'?'.join(results)
	}

def extract_torrents(data):
	results = [] 
	for torrent in movie_regex.findall(data):
		infohash = hash_regex.search(torrent[1]).group(1)
		magnet = 'magnet:?xt=urn:btih:%s'%infohash
		results.append({
			"name": torrent[0].decode('utf-8'),
			"info_hash": infohash.decode('utf-8'),
			"uri": provider.with_cookies("%s%s"%(provider.ADDON.getSetting('url'), torrent[1])).decode('utf-8'),
			# "uri": magnet.decode('utf-8'),
			# "seeds": torrent[3],
			# "peers": torrent[4]
		})
	return results

# Raw search
# query is always a string
def search(query):
	provider.log.info("DEBUUUUG")

	url_search = "%s/t?q=%s"%(provider.ADDON.getSetting('url'), query)
	resp = provider.POST(
		"%s/t"%provider.ADDON.getSetting('url'),
		{},
		{},
		"username=%s&password=%s"%(
			provider.ADDON.getSetting('username'),
			provider.ADDON.getSetting('password')
		)
	)
	resp = provider.GET(
		"%s/t"%provider.ADDON.getSetting('url'),
		{'q': query},
		{}
	)
	if int(resp.code) == 200:
		provider.log.info(resp.msg)
		et = extract_torrents(resp.data)
		provider.log.info(et)
		provider.log.info('>>>>>> %d torrents sent to Pulsar<<<<<<<'%len(et))
		return et
	else:
		message = "request returning %d %s"%(resp.code, resp.msg)
		provider.log.error(message)
		provider.notify(message)
		return

# Episode Payload Sample
# {
#     "imdb_id": "tt0092400",
#     "tvdb_id": "76385",
#     "title": "married with children",
#     "season": 1,
#     "episode": 1,
#     "titles": null
# }
def search_episode(episode):
	return search("%(title)s S%(season)02dE%(episode)02d" % episode)


# Movie Payload Sample
# Note that "titles" keys are countries, not languages
# The titles are also normalized (accents removed, lower case etc...)
# {
#     "imdb_id": "tt1254207",
#     "title": "big buck bunny",
#     "year": 2008,
#     "titles": {
#         "es": "el gran conejo",
#         "nl": "peach open movie project",
#         "ru": "большои кролик",
#         "us": "big buck bunny short 2008"
#     }
# }
def search_movie(movie):
	return search("%(imdb_id)s"%movie)


# This registers your module for use
provider.register(search, search_movie, search_episode)

del movie_regex
del hash_regex
