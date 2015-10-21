# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider, addon
import re, bencode, hashlib, urllib
import furious

movie_regex = re.compile(r'<a class="t_title" [^>]+>(.*?)</a>.*?href="([^"]*\.torrent)".*?<td.*?<td class=ac>(.*?)</td>.*?<td class="ac t_seeders">(.*?)</td><td class="ac t_leechers">(.*?)</td>', re.MULTILINE)

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
		'magnet': "magnet:?%s"%'&'.join(results)
	}

def extract_torrents(data, min_size, max_size):
	results = []
	count = 0
	for torrent in movie_regex.findall(data):
		if count >= int(provider.get_setting('max_magnets')):
			provider.log.info('filtering: too many results')
			break
		size = furious.human2bytes(torrent[2])
		if size < min_size or size > max_size:
			provider.log.info('filtering (not in size range):%s %d<%d<%d'%(
				torrent[0], min_size, size, max_size
			))
			continue
		if provider.get_setting('pulsar_integration') == 'torrent':
			provider.log.info('found: %s at %s'%(torrent[0], torrent[1]))
			url = "%s%s"%(provider.get_setting('url_address'), urllib.quote(torrent[1]))
			results.append({
				'name': torrent[0],
				'info_hash': hashlib.sha1(url).hexdigest(),
				'uri': provider.with_cookies(url),
				'seeds': int(torrent[3]),
				'peers': int(torrent[4]),
				'size': size
			})
			count += 1
		elif provider.get_setting('pulsar_integration') == 'magnet':
			provider.log.info('downloading %s'%torrent[1])
			resp = provider.GET(
				"%s%s"%(provider.get_setting('url_address'), urllib.quote(torrent[1]))
			)
			if int(resp.code) == 200:
				provider.log.info("torrent loaded")
				parsed = parseTorrent(resp.data)
				results.append({
					"name": parsed['name'],
					"info_hash": parsed['info_hash'],
					"uri": parsed['magnet'],
					"seeds": int(torrent[3]),
					"peers": int(torrent[4])
					# "size": furious.human2bytes(torrent[2])
					# "trackers": parsed['trackers']
				})
				count += 1

	# print results
	return results

# Raw search
# query is always a string
def search(query, tags=[], min_size=0, max_size=10*2**30):
	resp = provider.POST(
		"%s/t"%provider.get_setting('url_address'),
		{},
		{},
		"username=%s&password=%s"%(
			provider.get_setting('username'),
			provider.get_setting('password')
		)
	)
	query_obj = {'q': query}
	for tag in tags:
		query_obj[tag] = ''

	provider.log.info(query_obj)
	resp = provider.GET(
		"%s/t"%provider.get_setting('url_address'),
		query_obj,
		{}
	)
	if int(resp.code) == 200:
		provider.log.info('Connected')
		et = extract_torrents(resp.data, min_size, max_size)
		provider.log.info('>>>>>> %d torrents sent to Pulsar<<<<<<<'%len(et))
		provider.notify('%d torrents found'%len(et))
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
	return search(
		"%(imdb_id)s+S%(season)02dE%(episode)02d"%episode,
		furious.get_tags(provider, 'tv_tag_'),
		float(provider.get_setting('TV_min_size')) * 2**30,
		float(provider.get_setting('TV_max_size')) * 2**30
	)

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
	return search(
		"%(imdb_id)s"%movie,
		furious.get_tags(provider, 'movie_tag_'),
		float(provider.get_setting('movie_min_size')) * 2**30,
		float(provider.get_setting('movie_max_size')) * 2**30
	)


# This registers your module for use
provider.register(search, search_movie, search_episode)

del movie_regex
