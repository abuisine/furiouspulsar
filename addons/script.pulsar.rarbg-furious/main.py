# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider
import furious

app_id = 'script.pulsar.rarbg-furious'

def get_token():
	resp = provider.GET(provider.get_setting('url_address'),
		{
			'get_token': 'get_token',
			'app_id': app_id
		}
	)
	if int(resp.code) == 200:
	  json = resp.json()
	  provider.log.info('Got token: %s'%json['token'])
	  return json['token']
	else:
	  provider.log.info('error')
	  provider.log.info(resp.msg)
	  provider.notify('Error getting token')
	  return ''

def convert_torrentapi2pulsar(response, min_size, max_size):
	results = []
	count = 0
	if 'torrent_results' in response:
		torrents = response['torrent_results']
		for torrent in torrents:
			size = torrent['size']
			if size < min_size or size > max_size:
				continue
			count += 1
			if count > int(provider.get_setting('max_magnets')):
				break
			results.append({
				"name": torrent['title'],
				"uri": torrent['download'],
				# "info_hash": string
				# "trackers": [string, ...]
				"size": size,
				"seeds": torrent['seeders'],
				"peers": torrent['leechers']
				# "resolution": int
				# "video_codec": int
				# "audio_codec": int
				# "rip_type": int
				# "scene_rating": int
				# "language": string (ISO 639-1)
			})
		provider.log.info('%d result(s) sent'%len(results))
		provider.notify('%d torrents found'%len(results))
		return results
	else:
		provider.log.info('Error: %d %s'%(response['error_code'], response['error']))
		return results

def get_tags(header):
	idx = 0
	tags = []
	while(provider.get_setting('%s%d'%(header, idx)) != ''):
		tag = provider.get_setting('%s%d'%(header, idx))
		if tag != 'N/A':
			tags.append(tag)
		idx += 1
	return tags

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
	token = get_token()
	tags = furious.get_tags(provider, 'tv_tag_')
	categories = ""
	for tag in tags:
		if categories == "":
			categories = tag
		else:
			categories += ';%s'%tag
	if token != '':
		resp = provider.GET(provider.get_setting('url_address'),
			{
				'token': token,
				'app_id': app_id,
				'mode': 'search',
				'sort': 'seeders',
				'format': 'json_extended',
				'search_imdb': "%(imdb_id)s"%episode,
				'search_string': "S%(season)02dE%(episode)02d"%episode,
				'category': categories
			}
		)
		if int(resp.code) == 200:
			return furious.process_results(provider, convert_torrentapi2pulsar(
				resp.json(),
				float(provider.get_setting('TV_min_size')) * 2**30,
				float(provider.get_setting('TV_max_size')) * 2**30
			))

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
	token = get_token()
	tags = furious.get_tags(provider, 'movie_tag_')
	categories = ""
	for tag in tags:
		if categories == "":
			categories = tag
		else:
			categories += ';%s'%tag
	if token != '':
		resp = provider.GET(provider.get_setting('url_address'),
			{
				'token': token,
				'app_id': app_id,
				'mode': 'search',
				'sort': 'seeders',
				'format': 'json_extended',
				'search_imdb': "%(imdb_id)s"%movie,
				'category': categories
			}
		)
		if int(resp.code) == 200:
			return furious.process_results(provider, convert_torrentapi2pulsar(
				resp.json(),
				float(provider.get_setting('movie_min_size')) * 2**30,
				float(provider.get_setting('movie_max_size')) * 2**30
			))

# This registers your module for use
provider.register(None, search_movie, search_episode)

del app_id