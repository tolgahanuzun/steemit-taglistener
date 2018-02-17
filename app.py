from steem import Steem
from datetime import datetime, date, timedelta


def tag_filter(tag, limit = 10):
    tag_search = Steem()
    tag_query = {
        "tag":tag,
        "limit": limit
        }
    tag_filters = tag_search.get_discussions_by_created(tag_query)
    yesterday_post = []
    import ipdb; ipdb.set_trace()
    for _tag in tag_filters:
        _create_time = datetime.strptime(_tag['created'], '%Y-%m-%dT%H:%M:%S')
        _yersterday = date.today() - timedelta(1) 
        if _yersterday.day ==  _create_time.day:
           yesterday_post.append(_tag)
        
        return yesterday_post

