from steem import Steem
from datetime import datetime, date, timedelta
from math import ceil, log, isnan
import requests

API = 'https://api.steemjs.com/'

def tag_filter(tag, limit = 10):
    tag_search = Steem()
    tag_query = {
        "tag":tag,
        "limit": limit
        }
    tag_filters = tag_search.get_discussions_by_created(tag_query)
    #yesterday_post = []
    #import ipdb; ipdb.set_trace()
    # for _tag in tag_filters:
    #     _create_time = datetime.strptime(_tag['created'], '%Y-%m-%dT%H:%M:%S')
    #     _yersterday = date.today() - timedelta(1) 
    #     if _yersterday.day ==  _create_time.day:
    #        yesterday_post.append(_tag)
        
    return tag_filters

def get_vp_rp(steemit_name):
    url = '{}get_accounts?names[]=%5B%22{}%22%5D'.format(API, steemit_name)
    data = requests.get(url).json()[0]
    vp = data['voting_power']
    _reputation = data['reputation']
    _reputation = int(_reputation)

    rep = str(_reputation)
    neg = True if rep[0] == '-' else False
    rep = rep[1:] if neg else rep
    srt = rep
    leadingDigits = int(srt[0:4])
    log_n = log(leadingDigits / log(10), 2.71828)
    n  = len(srt) - 1
    out = n + (log_n - int(log_n))
    if isnan(out): out = 0
    out = max(out - 9, 0)

    out = (-1 * out) if neg else (1 * out)
    out = out * 9 + 25
    out = int(out)
    return [ceil(vp / 100), out]