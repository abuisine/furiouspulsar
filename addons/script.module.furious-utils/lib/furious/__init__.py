import urllib, bencode, hashlib

class FuriousProvider(object):

  define1 = 'truc'

  def __init__(self, name, provider):
    self.name = name
    self.provider = provider
    self.authenticated = False
    self.token = ""
    self.authenticate()

  def authenticate(self):
    return

  def searchMovie(self, movie):
    return []

  def searchEpisode(self, episode):
    return []

  def search(self, query):
    return []  

  def filterPotentials(self, potentials):
    min_size = float(self.provider.get_setting('movie_min_size')) * 2**30
    max_size = float(self.provider.get_setting('movie_max_size')) * 2**30
    results = []
    count = 0
    filtered = 0
    for potential in potentials:
      self.provider.log.info('testing torrent')
      size = potential['size']
      if size < min_size or size > max_size:
        self.provider.log.info('filtered: %d < %d < %d'%(min_size, size, max_size))
        filtered += 1
        continue
      count += 1
      if count > int(self.provider.get_setting('max_magnets')):
        self.provider.log.info('filtered: too many results')
        filtered += 1
        break
      results.append(potential)
    self.provider.log.info('Results: %d OK, %d filtered'%(len(results), filtered))
    self.provider.notify('%d torrents found, [COLOR red]%d filtered[/COLOR]'%(len(results), filtered))
    return results

  def rankResults(self, results):
    mode = self.provider.get_setting('ranking_mode')
    multiplier = 0
    header = "[COLOR hotpink]F[/COLOR] "
    if mode == "1":
      header += "[COLOR lime]UP[/COLOR] "
      multiplier = int(self.provider.get_setting('upgrade_factor'))
      self.provider.log.info('Ranking upgrade')
    elif mode == "2":
      header += "[COLOR blue]DOWN[/COLOR] "
      multiplier = 1.0 / int(self.provider.get_setting('downgrade_factor'))
      self.provider.log.info('Ranking downgrade')

    for result in results:
      seeds = result['seeds']
      peers = result['peers']
      text = ""
      if multiplier != 0:
        text = "S%dP%d "%(seeds, peers)
        if 'seeds' in result:
          result['seeds'] = (max(int(round(multiplier * seeds)), 1), 0)[seeds == 0]
        if 'peers' in result:
          result['peers'] = (max(int(round(multiplier * peers)), 1), 0)[peers == 0]
      if 'name' in result:
        result['name'] = header + text + result['name']

    return results

  def decodeRawTorrent(self, data):
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

    self.provider.log.info('torrent decoded')
    return {
      'info_hash': sha1,
      'name': decoded_info["name"],
      'trackers': trackers,
      'magnet': "magnet:?%s"%'&'.join(results)
    }

  def forceMagnets(self, results):
    magnet_results = []
    for result in results:
      resp = self.provider.GET(result['uri'])
      if int(resp.code) == 200:
        self.provider.log.info('downloaded %s'%result['name'])
        parsed = self.decodeRawTorrent(resp.data)
        result["name"] = parsed['name']
        result["info_hash"] = parsed['info_hash']
        result["uri"] = parsed['magnet']
        magnet_results.append(result)
    return magnet_results

  def getTvTags(self):
    return self.__getTags('tv_tag_')

  def getMovieTags(self):
    return self.__getTags('movie_tag_')

  def __getTags(self, header):
    idx = 0
    tags = []
    while(self.provider.get_setting('%s%d'%(header, idx)) != ''):
      tag = self.provider.get_setting('%s%d'%(header, idx))
      if tag != 'N/A':
        tags.append(tag)
      idx += 1
    return tags

"""
Bytes-to-human / human-to-bytes converter.
Based on: http://goo.gl/kTQMs
Working with Python 2.x and 3.x.

Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
License: MIT
"""

# see: http://goo.gl/kTQMs
SYMBOLS = {
  'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
  'furious'       : ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'),
  'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa', 'zetta', 'iotta'),
  'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
  'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi', 'zebi', 'yobi'),
}

def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
  """
  Convert n bytes into a human readable string based on format.
  symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
  see: http://goo.gl/kTQMs

    >>> bytes2human(0)
    '0.0 B'
    >>> bytes2human(0.9)
    '0.0 B'
    >>> bytes2human(1)
    '1.0 B'
    >>> bytes2human(1.9)
    '1.0 B'
    >>> bytes2human(1024)
    '1.0 K'
    >>> bytes2human(1048576)
    '1.0 M'
    >>> bytes2human(1099511627776127398123789121)
    '909.5 Y'

    >>> bytes2human(9856, symbols="customary")
    '9.6 K'
    >>> bytes2human(9856, symbols="customary_ext")
    '9.6 kilo'
    >>> bytes2human(9856, symbols="iec")
    '9.6 Ki'
    >>> bytes2human(9856, symbols="iec_ext")
    '9.6 kibi'

    >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
    '9.8 K/sec'

    >>> # precision can be adjusted by playing with %f operator
    >>> bytes2human(10000, format="%(value).5f %(symbol)s")
    '9.76562 K'
  """
  n = int(n)
  if n < 0:
    raise ValueError("n < 0")
  symbols = SYMBOLS[symbols]
  prefix = {}
  for i, s in enumerate(symbols[1:]):
    prefix[s] = 1 << (i+1)*10
  for symbol in reversed(symbols[1:]):
    if n >= prefix[symbol]:
      value = float(n) / prefix[symbol]
      return format % locals()
  return format % dict(symbol=symbols[0], value=n)

def human2bytes(s):
  """
  Attempts to guess the string format based on default symbols
  set and return the corresponding bytes as an integer.
  When unable to recognize the format ValueError is raised.

    >>> human2bytes('0 B')
    0
    >>> human2bytes('1 K')
    1024
    >>> human2bytes('1 M')
    1048576
    >>> human2bytes('1 Gi')
    1073741824
    >>> human2bytes('1 tera')
    1099511627776

    >>> human2bytes('0.5kilo')
    512
    >>> human2bytes('0.1  byte')
    0
    >>> human2bytes('1 k')  # k is an alias for K
    1024
    >>> human2bytes('12 foo')
    Traceback (most recent call last):
      ...
    ValueError: can't interpret '12 foo'
  """
  init = s
  num = ""
  while s and s[0:1].isdigit() or s[0:1] == '.':
    num += s[0]
    s = s[1:]
  num = float(num)
  letter = s.strip()
  for name, sset in SYMBOLS.items():
    if letter in sset:
      break
  else:
    if letter == 'k':
      # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
      sset = SYMBOLS['customary']
      letter = letter.upper()
    else:
      raise ValueError("can't interpret %r" % init)
  prefix = {sset[0]:1}
  for i, s in enumerate(sset[1:]):
    prefix[s] = 1 << (i+1)*10
  return int(num * prefix[letter])