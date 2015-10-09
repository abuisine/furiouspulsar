# coding: utf-8

# First, you need to import the pulsar module
# Make sure you declare Pulsar as dependency in the addon.xml or it won't work
# You can read it at:
# https://github.com/steeve/plugin.video.pulsar/blob/master/resources/site-packages/pulsar/provider.py
from pulsar import provider

def get_token():
	resp = provider.GET(provider.get_setting('url_address'),
		{'get_token': 'get_token'}
	)
	if int(resp.code) == 200:
		provider.log.info(resp.json())

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
		return et
	else:
		message = "request returning %d %s"%(resp.code, resp.msg)
		provider.log.error(message)
		provider.notify(message)
		return

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
	get_token()
	# return search(
	# 	"%(imdb_id)s+S%(season)02dE%(episode)02d"%episode,
	# 	get_tags('tv_tag_'),
	# 	float(provider.get_setting('TV_min_size')) * 2**30,
	# 	float(provider.get_setting('TV_max_size')) * 2**30
	# )

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
	get_token()
	# return search(
	# 	"%(imdb_id)s"%movie,
	# 	get_tags('movie_tag_'),
	# 	float(provider.get_setting('movie_min_size')) * 2**30,
	# 	float(provider.get_setting('movie_max_size')) * 2**30
	# )


# This registers your module for use
provider.register(search, search_movie, search_episode)