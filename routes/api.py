"""
REST API blueprint mounted at /api. Returns JSON only.
Database work is done in models.py; calculations come from supply_chain_model.py.
"""
from flask import Blueprint, abort, jsonify, request

import models
import supply_chain_model as scm

api = Blueprint("api", __name__, url_prefix="/api")

AVG_SPEED_KMH = 30
MAX_PAGE_SIZE = 50


def _error(message, status=400):
    return jsonify(error=message), status


def _body():
    return request.get_json(silent=True) or {}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _paging():
    """Read ?page= and ?size=. Returns (page, size, offset) or None if invalid."""
    page = request.args.get("page", 1, type=int)
    size = min(request.args.get("size", 10, type=int), MAX_PAGE_SIZE)
    if page < 1 or size < 1:
        return None
    return page, size, (page - 1) * size


def _require_stop(stop_id):
    if not models.stop_exists(stop_id):
        abort(404, description="Stop not found")


# ---------- stops ----------

@api.get("/stops")
def list_stops():
    paging = _paging()
    if paging is None:
        return _error("page and size must be positive")
    page, size, offset = paging
    items = models.list_stops(request.args.get("route_id", type=int), size, offset)
    return jsonify(page=page, size=size, items=items)


@api.get("/stops/<int:stop_id>")
def get_stop(stop_id):
    stop = models.get_stop(stop_id)
    if not stop:
        abort(404)
    distance = stop.get("distance_to_cbd_km")
    stop["eta_minutes"] = scm.eta_minutes(float(distance), AVG_SPEED_KMH, 0) if distance else None
    stop["confidence"] = scm.confidence_score(stop["pin_reports"], stop["gps_confirms"])
    return jsonify(stop)


@api.post("/stops")
def create_stop():
    data = _body()
    name = (data.get("name") or "").strip() if isinstance(data.get("name"), str) else ""
    route_id = data.get("route_id")
    if not name:
        return _error("name is required")
    if route_id is not None and (not _is_int(route_id) or not models.route_exists(route_id)):
        return _error("route_id must be an existing route", 404)
    try:
        distance = float(data["distance_to_cbd_km"]) if data.get("distance_to_cbd_km") is not None else None
    except (TypeError, ValueError):
        return _error("distance_to_cbd_km must be a number")
    if distance is not None and distance < 0:
        return _error("distance_to_cbd_km cannot be negative")
    stop_id = models.create_stop(name, route_id, distance, data.get("latitude"), data.get("longitude"))
    return jsonify(stop_id=stop_id), 201


@api.patch("/stops/<int:stop_id>")
def update_stop(stop_id):
    data = _body()
    fields = {}
    if isinstance(data.get("name"), str) and data["name"].strip():
        fields["name"] = data["name"].strip()
    if "distance_to_cbd_km" in data:
        try:
            fields["distance_to_cbd_km"] = float(data["distance_to_cbd_km"])
        except (TypeError, ValueError):
            return _error("distance_to_cbd_km must be a number")
        if fields["distance_to_cbd_km"] < 0:
            return _error("distance_to_cbd_km cannot be negative")
    if not fields:
        return _error("Provide name or distance_to_cbd_km")
    if not models.update_stop(stop_id, fields):
        abort(404)
    return jsonify(ok=True)


# ---------- demand ----------

@api.get("/demand-reports")
def list_demand_reports():
    paging = _paging()
    if paging is None:
        return _error("page and size must be positive")
    page, size, offset = paging
    items = models.list_demand_reports(request.args.get("stop_id", type=int), size, offset)
    return jsonify(page=page, size=size, items=items)


@api.get("/demand-reports/<int:report_id>")
def get_demand_report(report_id):
    report = models.get_demand_report(report_id)
    if not report:
        abort(404)
    return jsonify(report)


@api.post("/demand-reports")
def create_demand_report():
    data = _body()
    stop_id, waiting = data.get("stop_id"), data.get("waiting_passengers")
    if not _is_int(stop_id) or not _is_int(waiting) or not 0 <= waiting <= 1000:
        return _error("stop_id (int) and waiting_passengers (0-1000) required")
    _require_stop(stop_id)
    return jsonify(report_id=models.create_demand_report(stop_id, waiting)), 201


@api.get("/heatmap")
def heatmap():
    result = []
    for row in models.stops_with_demand():
        intensity, level = scm.heat_map_entry(row["waiting"], row["taxis"])
        result.append({**row, "intensity": intensity, "level": level})
    return jsonify(result)


# ---------- taxi positions ----------

@api.get("/taxi-positions")
def list_taxi_positions():
    active_only = request.args.get("active", "true").lower() != "false"
    items = models.list_taxi_positions(active_only, request.args.get("stop_id", type=int))
    return jsonify(items=items)


@api.get("/taxi-positions/<int:position_id>")
def get_taxi_position(position_id):
    position = models.get_taxi_position(position_id)
    if not position:
        abort(404)
    return jsonify(position)


@api.post("/taxi-positions")
def checkin_taxi():
    data = _body()
    stop_id, seats = data.get("stop_id"), data.get("seats_available", 15)
    driver_id = data.get("driver_id")
    if not _is_int(stop_id) or not _is_int(seats) or not 0 <= seats <= 15:
        return _error("stop_id (int) and seats_available (0-15) required")
    if driver_id is not None and not _is_int(driver_id):
        return _error("driver_id must be an integer")
    _require_stop(stop_id)
    return jsonify(position_id=models.create_taxi_position(stop_id, seats, driver_id)), 201


@api.patch("/taxi-positions/<int:position_id>")
def update_taxi_position(position_id):
    is_active = _body().get("is_active")
    if not isinstance(is_active, bool):
        return _error("is_active (true/false) required")
    if not models.set_taxi_active(position_id, is_active):
        abort(404)
    return jsonify(ok=True)


# ---------- problems ----------

@api.get("/problems")
def list_problems():
    status = request.args.get("status", "open")
    if status not in ("open", "resolved"):
        return _error("status must be open or resolved")
    paging = _paging()
    if paging is None:
        return _error("page and size must be positive")
    page, size, offset = paging
    return jsonify(page=page, size=size, items=models.list_problems(status, size, offset))


@api.get("/problems/<int:problem_id>")
def get_problem(problem_id):
    problem = models.get_problem(problem_id)
    if not problem:
        abort(404)
    return jsonify(problem)


@api.post("/problems")
def create_problem():
    data = _body()
    stop_id = data.get("stop_id")
    problem_type = data.get("problem_type").strip() if isinstance(data.get("problem_type"), str) else ""
    description = data.get("description") if isinstance(data.get("description"), str) else ""
    if not _is_int(stop_id) or not problem_type:
        return _error("stop_id and problem_type required")
    _require_stop(stop_id)
    return jsonify(problem_id=models.create_problem(stop_id, problem_type, description)), 201


@api.patch("/problems/<int:problem_id>")
def update_problem(problem_id):
    status = _body().get("status")
    if status not in ("open", "resolved"):
        return _error("status must be open or resolved")
    if not models.set_problem_status(problem_id, status):
        abort(404)
    return jsonify(ok=True)
