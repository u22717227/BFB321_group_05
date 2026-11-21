"""
Page routes: HTML pages and form actions (form post -> redirect -> flash message).
Database work is done in models.py; calculations come from supply_chain_model.py.
"""
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import models
import supply_chain_model as scm

pages = Blueprint("pages", __name__)

AVG_SPEED_KMH = 30      # assumed minibus speed for ETA
SPARE_TAXIS = 20        # spare taxis available for the deployment plan
SEATS_PER_TAXI = 15
REPORT_TYPES = {
    "Taxi stops here": "stop_confirm",
    "I was picked up safely": "safe_pickup",
    "I felt safe while waiting at this stop": "safety_rating",
}


def role_required(*roles):
    """Form actions limited to signed-in users with one of the given roles."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash(f"Please log in as a {' or '.join(roles)} to do that.", "error")
                return redirect(url_for("pages.login"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _done(message, ok, endpoint):
    """Flash a green (ok) or red message and go back to a page."""
    flash(message, "success" if ok else "error")
    return redirect(url_for(endpoint))


# ---------- calculations for the pages ----------

def _home_kpis():
    stops = models.stops_with_evidence()
    demand = models.stops_with_demand()
    seats = models.active_seat_counts()
    history = models.recent_demand_history()

    verified = sum(1 for s in stops
                   if scm.confidence_score(s["pin_reports"], s["gps_confirms"]) >= 0.5)
    waits = [d["waiting"] for d in demand]
    under_served = sum(1 for d in demand if scm.demand_intensity(d["waiting"], d["taxis"]) > 1)
    occupancy = [scm.occupancy_percentage(SEATS_PER_TAXI - s) for s in seats]
    total = len(stops)
    return {
        "total_stops": total,
        "verified_pct": round(100 * verified / total, 1) if total else 0,
        "open_problems": models.count_open_problems(),
        "active_taxis": len(seats),
        "under_served": under_served,
        "avg_wait": round(sum(waits) / len(waits), 1) if waits else 0,
        "forecast": scm.forecast_demand(history) if history else 0,
        "occupancy": round(sum(occupancy) / len(occupancy), 1) if occupancy else 0,
    }


def _live_stop(stop):
    distance = stop["distance_to_cbd_km"]
    eta = scm.eta_minutes(float(distance), AVG_SPEED_KMH, 0) if distance else None
    confidence = scm.confidence_score(stop["pin_reports"], stop["gps_confirms"])
    return {
        "name": stop["name"],
        "route": stop["route"] or "Unknown",
        "eta": f"{eta} min" if eta else "No GPS",
        "confidence": confidence,
        "verified": confidence >= 0.5,
    }


def _heat_map():
    rows = models.stops_with_demand()
    heat_map = []
    for row in rows:
        intensity, level = scm.heat_map_entry(row["waiting"], row["taxis"])
        heat_map.append({"stop": row["name"], "waiting": row["waiting"],
                         "taxis": row["taxis"], "intensity": intensity, "level": level})
    deployment = scm.deploy_taxis({r["name"]: (r["waiting"], r["taxis"]) for r in rows}, SPARE_TAXIS)
    return heat_map, deployment


# ---------- pages ----------

@pages.route("/")
def index():
    return render_template("index.html", kpis=_home_kpis())


@pages.route("/stops")
def stops():
    live_stops = [_live_stop(s) for s in models.stops_with_evidence()]
    problems = models.list_problems("open")
    return render_template("stops.html", live_stops=live_stops, problems=problems,
                           stops=models.list_stop_choices())


@pages.route("/demand")
def demand():
    heat_map, deployment = _heat_map()
    return render_template("demand.html", heat_map=heat_map, deployment=deployment,
                           stops=models.list_stop_choices(),
                           active_taxis=models.list_taxi_positions(active_only=True))


@pages.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        return _submit_stop_report()
    return render_template("report.html", stops=models.list_stop_choices())


def _submit_stop_report():
    stop_name = request.form.get("stop")
    report_type = request.form.get("type")
    safety = request.form.get("safety", type=int)
    if not stop_name or report_type not in REPORT_TYPES or safety not in range(1, 6):
        return _done("Please fill all fields correctly.", False, "pages.report")
    stop_id = models.get_stop_id_by_name(stop_name)
    if stop_id is None:
        return _done("Stop not found.", False, "pages.report")
    models.create_verification(stop_id, REPORT_TYPES[report_type], safety, session.get("user_id"))
    return _done("Report submitted successfully!", True, "pages.report")


# ---------- login ----------

@pages.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = models.get_user_by_email(request.form.get("email"))
        if user and check_password_hash(user["password_hash"], request.form.get("password") or ""):
            session.update(user_id=user["user_id"], role=user["role"], name=user["full_name"])
            return _done(f"Welcome, {user['full_name']}!", True, "pages.index")
        flash("Invalid credentials.", "error")
    return render_template("login.html")


@pages.route("/logout")
def logout():
    session.clear()
    return _done("Logged out.", True, "pages.index")


# ---------- form actions ----------

@pages.route("/demand/report", methods=["POST"])
def demand_report_form():
    stop_id = request.form.get("stop_id", type=int)
    waiting = request.form.get("waiting_passengers", type=int)
    if stop_id is None or waiting is None or not 0 <= waiting <= 1000:
        return _done("Please enter a valid stop and number of waiting passengers (0-1000).",
                     False, "pages.demand")
    if not models.stop_exists(stop_id):
        return _done("Stop not found.", False, "pages.demand")
    models.create_demand_report(stop_id, waiting, session.get("user_id"))
    return _done("Demand report saved.", True, "pages.demand")


@pages.route("/problems/report", methods=["POST"])
def problem_report_form():
    stop_id = request.form.get("stop_id", type=int)
    problem_type = (request.form.get("problem_type") or "").strip()
    description = (request.form.get("description") or "").strip()
    if stop_id is None or not problem_type:
        return _done("Choose a stop and describe the problem.", False, "pages.stops")
    if not models.stop_exists(stop_id):
        return _done("Stop not found.", False, "pages.stops")
    models.create_problem(stop_id, problem_type, description, session.get("user_id"))
    return _done("Problem reported.", True, "pages.stops")


@pages.route("/problems/<int:problem_id>/resolve", methods=["POST"])
@role_required("association")
def resolve_problem_form(problem_id):
    if models.resolve_open_problem(problem_id):
        return _done("Problem resolved.", True, "pages.stops")
    return _done("Problem was already closed.", False, "pages.stops")


@pages.route("/taxis/checkin", methods=["POST"])
@role_required("driver", "association")
def taxi_checkin_form():
    stop_id = request.form.get("stop_id", type=int)
    seats = request.form.get("seats_available", type=int)
    if stop_id is None or seats is None or not 0 <= seats <= SEATS_PER_TAXI:
        return _done("Choose a stop and a seat count between 0 and 15.", False, "pages.demand")
    if not models.stop_exists(stop_id):
        return _done("Stop not found.", False, "pages.demand")
    models.create_taxi_position(stop_id, seats, session.get("user_id"))
    return _done("Taxi checked in.", True, "pages.demand")


@pages.route("/taxis/<int:position_id>/checkout", methods=["POST"])
@role_required("driver", "association")
def taxi_checkout_form(position_id):
    if models.check_out_taxi(position_id):
        return _done("Taxi checked out.", True, "pages.demand")
    return _done("That taxi was already inactive.", False, "pages.demand")
