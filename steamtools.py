import requests
from requests.exceptions import SSLError
import time
import pandas as pd
import dataset

DB = dataset.connect('sqlite:///steamdata.db')


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


def finedetails(id):
    url = "https://steamspy.com/api.php"
    json_data = get_request(url, parameters={"request": "appdetails", "appid": id})
    print(f'getting data for id: {id}')

    tags = json_data['tags']
    languages = json_data['languages']
    genres = json_data['genre']

    tagtable = DB['tags']
    if not tagtable:
        tagtable = DB.create_table('tags', primary_id='appid', primary_type=DB.types.text)
    for tag in tags:
        if tag not in tagtable.columns:
            tagtable.create_column(tag, default=0)
    tagtable.insert(tags)

    languagetable = DB['languages']
    languages = {ling: 1 for ling in languages}
    if not languagetable:
        languagetable = DB.create_table('languages', primary_id='appid', primary_type=DB.types.text)
    for tongue in languages:
        if tongue not in languagetable.columns:
            languagetable.create_column(tongue, default=0)
    languagetable.insert(languages)

    genretable = DB['genre']
    genres = {gen: 1 for gen in genres}
    if not genretable:
        genretable = DB.create_table('genre', primary_id='appid', primary_type=DB.types.text)
    for gen in languages:
        if gen not in genretable.columns:
            genretable.create_column(gen, default=0)
    genretable.insert(genres)
    time.sleep(1)


if __name__ == '__main__':
    populate_applist()
    for row in DB['app']:
        finedetails(row['appid'])
