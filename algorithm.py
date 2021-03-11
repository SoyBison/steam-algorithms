import numpy as np
import scipy.stats as st
import sqlite3
import pandas as pd
from sklearn.preprocessing import Normalizer
from sklearn.linear_model import SGDClassifier

DB = sqlite3.connect('steamdata')

TAGDB = pd.read_sql_query('SELECT * FROM tags', DB)
GAMEDB = pd.read_sql_query('SELECT * FROM app', DB)


def wilson_score(successes, failures, alpha=0.05):
    n = successes + failures
    phat = successes / n
    z = st.norm.ppf(1-(alpha/2))

    return (phat + z**2 / (2*n) - z * np.sqrt((phat*(1-phat) + z**2 / (4*n)) / n))/(1 + z**2 / n)

class Game:
    def __init__(self, x: np.ndarray, q: float, num_players_2wk: int, discount: int):
        self.x = x
        self.q = q
        self.num_players_2wk = num_players_2wk
        self.discount = discount

    @classmethod
    def random(cls):
        x = np.random.uniform(size=425)
        x = Normalizer(norm='l1').fit_transform(x)
        np2wk = np.random.randint(0, 10000)
        return cls(x, np.random.uniform)

    @classmethod
    def from_id(cls, appid):
        tagvec = TAGDB[TAGDB['appid'] == appid].drop(['appid', 'id']).values[0]
        x = Normalizer(norm='l1').fit_transform(tagvec)
        gamedata = GAMEDB[GAMEDB['appid'] == appid][0]
        q = wilson_score(gamedata['positive'], gamedata['negative'])
        num_players_2wk = gamedata['average_2weeks']
        discount = int(gamedata['discount'])
        return cls(x, q, num_players_2wk, discount)


class User:
    def __init__(self):
        self.x_bar = np.random.uniform(size=425)
        self.x_bar = Normalizer(norm='l1').fit_transform(self.x_bar)
        self.alpha = np.random.uniform()

    def score(self, game: Game):
        cossim = self.x_bar.dot(game.x) / (np.linalg.norm(self.x_bar) * np.linalg.norm(game.x))
        score = self.alpha * cossim + (1 - self.alpha) * game.q
        return score


class UserStream:
    def __init__(self, n=1000):
        self.n = n
        self.t = 0

    def __next__(self):
        if self.t < self.n:
            return User()
        else:
            raise StopIteration

    def __iter__(self):
        return [User() for _ in range(self.n - self.t)]


class Recommender:
    def __init__(self):
        pass
