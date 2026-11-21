import pymysql
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = pymysql.connect(
            **current_app.config["DB"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
