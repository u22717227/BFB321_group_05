"""
Eyabantu Taxi Program - Flask application factory
BFB 321 Group 05

app.py only sets the app up: configuration, logging, database teardown,
blueprints and error handlers. Routes live in routes/, SQL in models.py.
"""
import logging
import os
from datetime import date, datetime
from decimal import Decimal

import pymysql
from flask import Flask, flash, jsonify, redirect, request, url_for

from config import config
from db import close_db, get_db
from routes.api import api
from routes.pages import pages


def _json_default(value):
    """Let jsonify handle MySQL DECIMAL and date/time values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(value)}")


def _is_api_request():
    return request.path.startswith("/api/")


def _register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=getattr(e, "description", "Bad request")), 400

    @app.errorhandler(404)
    def not_found(e):
        if _is_api_request():
            # Our own abort(404, description=...) messages; Flask's default becomes "Not found"
            message = e.description if "requested URL" not in (e.description or "") else "Not found"
            return jsonify(error=message), 404
        return "<h1>Page not found</h1><p><a href='/'>Back to home</a></p>", 404

    @app.errorhandler(pymysql.err.IntegrityError)
    def integrity_error(e):
        # Duplicate keys or broken foreign keys: a clear message instead of a 500.
        app.logger.warning("Integrity error: %s", e)
        get_db().rollback()
        if _is_api_request():
            return jsonify(error="Duplicate or invalid data"), 409
        flash("That record already exists or refers to missing data.", "error")
        return redirect(request.referrer or url_for("pages.index"))

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Server error on %s", request.path)
        try:
            get_db().rollback()
        except Exception:
            pass
        if _is_api_request():
            return jsonify(error="Internal server error"), 500
        return "<h1>Something went wrong</h1><p><a href='/'>Back to home</a></p>", 500


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    logging.basicConfig(filename="eyabantu.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    app.logger.setLevel(logging.INFO)

    app.json.default = _json_default
    app.teardown_appcontext(close_db)
    app.register_blueprint(pages)
    app.register_blueprint(api)
    _register_error_handlers(app)
    return app


app = create_app(os.getenv("APP_ENV", "production"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
