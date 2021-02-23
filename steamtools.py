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

    populate_applist(_p=_p+1)
