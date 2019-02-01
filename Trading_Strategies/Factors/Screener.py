import pandas as pd
import pymongo as pm


class Screener :
    db = None
    coll_price = None
    coll_factor = None

    universe = []

    def __init__(self, db):
        pass

    def initUniverse(self, universe='ALL', filter=None):

