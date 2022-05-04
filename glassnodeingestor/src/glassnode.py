import json
import requests
import datetime
import iso8601
import pandas as pd

class GlassnodeClient:

  def __init__(self, api_key):
    self._api_key = api_key

  def get(self, url, a='BTC', i='24h', c='native', s=None, u=None):
    p = dict()
    p['a'] = a
    p['i'] = i
    p['c'] = c

    if s is not None:
      try:
        p['s'] = iso8601.parse_date(s).strftime('%s')
      except ParseError:
        p['s'] = s

    if u is not None:
      try:
        p['u'] = iso8601.parse_date(u).strftime('%s')
      except ParseError:
        p['u'] = s

    p['api_key'] = self._api_key

    r = requests.get(url, params=p,timeout = 2)
    if r.status_code != 200:
      raise ValueError("Error: %s" % r.text)

    try:
        result = json.loads(r.text)
        # t shows timestamp, often v for result, but other values as well
        if len(result) > 0:
          if result[0].get("t") is not None:
            # if we have a timestamp in response
            result = pd.DataFrame(result)
            result = result.set_index("t")
          else:
            raise ValueError("! no timestamp in response")
        return result
    except Exception as e:
        # check for non of t are in the columns
        print("problem with response: ", r.text)
        raise
