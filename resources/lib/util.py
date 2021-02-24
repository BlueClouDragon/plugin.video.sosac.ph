import xbmc
import sys
import re
import pickle
import http.cookiejar
import urllib
import urllib.error
import urllib.request
import traceback
from . import cloudflare
from html.entities import name2codepoint as n2cp


UA = 'Mozilla/6.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.5) Gecko/2008092417 Firefox/3.0.3'
_cookie_jar = None
CACHE_COOKIES = 'cookies'


def _substitute_entity(match):
    ent = match.group(3)
    if match.group(1) == '#':
        # decoding by number
        if match.group(2) == '':
            # number is in decimal
            return chr(int(ent))
        elif match.group(2) == 'x':
            # number is in hex
            return chr(int('0x' + ent, 16))
    else:
        # they were using a name
        cp = n2cp.get(ent)
        if cp:
            return chr(cp)
        else:
            return match.group()


def decode_html(data):
    if not type(data) == str:
        return data
    try:
        if not type(data) == str:
            data = str(data, 'utf-8', errors='ignore')
        entity_re = re.compile(r'&(#?)(x?)(\w+);')
        return entity_re.subn(_substitute_entity, data)[0]
    except:
        traceback.print_exc()
        return data


def request(url, headers=None):
    if headers is None:
        headers = {}
    debug('request: %s' % url)
    req = urllib.request.Request(url, headers=headers)
    req.add_header('User-Agent', UA)
    if _cookie_jar is not None:
        _cookie_jar.add_cookie_header(req)
    try:
        response = urllib.request.urlopen(req)
        data = response.read()
        response.close()
    except urllib.error.HTTPError as error:
        data = _solve_http_errors(url, error)
    debug('len(data) %s' % len(data))
    return data.decode("utf-8")


def _solve_http_errors(url, error):
    global _cookie_jar
    data = error.read()
    if error.code == 503 and 'cf-browser-verification' in data:
        data = cloudflare.solve(url, _cookie_jar, UA)
    error.close()
    return data


def params(url=None):
    if not url:
        url = sys.argv[2]
    param = {}
    paramstring = url
    if len(paramstring) >= 2:
        params = url
        cleanedparams = params.replace('?', '')
        if params[len(params) - 1] == '/':
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    for p in param.keys():
        param[p] = bytes.fromhex(param[p]).decode('utf-8')
    return param


def debug(text):
    xbmc.log(str([text]), xbmc.LOGDEBUG)


def info(text):
    xbmc.log(str([text]), xbmc.LOGINFO)


def error(text):
    xbmc.log(str([text]), xbmc.LOGERROR)


def cache_cookies(cache=None):
    """
    Saves cookies to cache
    """
    global _cookie_jar
    if _cookie_jar and cache is not None:
        cache.set(CACHE_COOKIES, _cookie_jar.dump())
    else:
        try:
            _cookie_jar.cache.set(CACHE_COOKIES, _cookie_jar.dump())
        except:
            pass


class _StringCookieJar(http.cookiejar.LWPCookieJar):

    def __init__(self, string=None, filename=None, delayload=False, policy=None, cache=None):
        self.cache = cache
        http.cookiejar.LWPCookieJar.__init__(self, filename, delayload, policy)
        if string and len(string) > 0:
            self._cookies = pickle.loads(str(string))

    def dump(self):
        return pickle.dumps(self._cookies)


def init_urllib(cache=None):
    """
    Initializes urllib cookie handler
    """
    global _cookie_jar
    data = None
    if cache is not None:
        data = cache.get(CACHE_COOKIES)
        _cookie_jar = _StringCookieJar(data, cache=cache)
    else:
        _cookie_jar = _StringCookieJar(data)
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cookie_jar))
    urllib.request.install_opener(opener)
