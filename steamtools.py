import requests
from requests.exceptions import SSLError, ConnectionError
import time
import pandas as pd
import dataset
import re
import json

from sqlalchemy.exc import OperationalError

DB = dataset.connect('sqlite:///steamdata.db')
try:
    KNOWN_APPS = DB.query('SELECT appid FROM tags')
    KNOWN_APPS = {a['appid'] for a in KNOWN_APPS}
except OperationalError:
    KNOWN_APPS = set() 

def get_request(url, parameters=None):
    """Return json-formatted response of a get request using optional parameters.
    Shamelessly stolen from https://nik-davis.github.io/posts/2019/steam-data-collection/

    Parameters
    ----------
    url : string
    parameters : {'parameter': 'value'}
        parameters to pass as part of get request

    Returns
    -------
    json_data
        json-formatted response (dict-like)
    """
    try:
        response = requests.get(url=url, params=parameters)
    except SSLError as s:
        print('SSL Error:', s)

        for i in range(5, 0, -1):
            print('\rWaiting... ({})'.format(i), end='')
            time.sleep(1)
        print('\rRetrying.' + ' ' * 10)

        # recusively try again
        return get_request(url, parameters)

    if response:
        return response.json()
    else:
        # response is none usually means too many requests. Wait and try again
        print('No response, waiting 10 seconds...')
        time.sleep(10)
        print('Retrying.')
        return get_request(url, parameters)


def populate_applist(_p=0):
    url = "https://steamspy.com/api.php"

    json_data = get_request(url, parameters={"request": "all", "page": _p})

    if len(json_data) == 0:
        return
    steam_spy_all = pd.DataFrame.from_dict(json_data, orient='index')
    applist = steam_spy_all.sort_values('appid').reset_index(drop=True)

    records = applist.to_dict('records')
    apptable = DB['app']
    apptable.insert_many(records)
    print(f'Populated page {_p}')
    time.sleep(60)
    populate_applist(_p=_p+1)


def finedetails(appid):
    url = "https://steamspy.com/api.php"

    if appid in KNOWN_APPS:
        print(f'Already scraped data for id: {appid}, skipping...')
        return
    else:
        print(f'getting data for id: {appid}')
    try:
        json_data = get_request(url, parameters={"request": "appdetails", "appid": appid})
    except (json.decoder.JSONDecodeError, ConnectionError):
        time.sleep(10)
        print(f'Data scrape for id: {appid} failed, retrying.')
        finedetails(appid)
        return
    tags = json_data['tags']
    languages = json_data['languages']
    genres = json_data['genre']
    primary = {'appid': appid}

    tagtable = DB['tags']
    tags = {re.sub('[- .\'+]+', '', k): tags[k] for k in tags if k!=''}
    if not tagtable:
        tagtable = DB.create_table('tags', primary_id='appid', primary_type=DB.types.text)
    for tag in tags:
        if tag not in tagtable.columns:
            tagtable.create_column(tag, default=0, type=DB.types.integer)
    tags.update(primary)
    tagtable.insert(tags)

    languagetable = DB['languages']
    if languages:
        languages = {re.sub('[- .\'+]+', '', ling): 1 for ling in languages.split(',') if ling!=''}
        if not languagetable:
            languagetable = DB.create_table('languages', primary_id='appid', primary_type=DB.types.text)
        for tongue in languages:
            if tongue not in languagetable.columns:
                languagetable.create_column(tongue, default=0, type=DB.types.integer)
        languages.update(primary)
        languagetable.insert(languages)

    genretable = DB['genre']
    if genres:
        genres = {re.sub('[- .\'+]+', '', gen): 1 for gen in genres.split(',') if gen!=''}
        if not genretable:
            genretable = DB.create_table('genre', primary_id='appid', primary_type=DB.types.text)
        for gen in genres:
            if gen not in genretable.columns:
                genretable.create_column(gen, default=0, type=DB.types.integer)
        genres.update(primary)
        genretable.insert(genres)
        time.sleep(1)


if __name__ == '__main__':
    # populate_applist()
    for row in DB['app']:
        finedetails(row['appid'])
