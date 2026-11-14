"""
Database layer for Eyabantu.

Every SQL query lives here. Routes call these functions and never write SQL
themselves. Table and column names match schema.sql and docs/erd.png.
All values are passed as %s parameters (no string-built SQL).
"""
from db import get_db

# Active taxis and stop confirmations per stop, reused by several queries
_ACTIVE_TAXIS = """(SELECT COUNT(*) FROM taxi_positions tp
                    WHERE tp.stop_id = s.stop_id AND tp.is_active = 1)"""
_STOP_CONFIRMS = """(SELECT COUNT(*) FROM verification_reports vr
                     WHERE vr.stop_id = s.stop_id AND vr.report_type = 'stop_confirm')"""
_LATEST_WAITING = """COALESCE((SELECT waiting_passengers FROM demand_reports dr
                               WHERE dr.stop_id = s.stop_id
                               ORDER BY dr.reported_at DESC, dr.report_id DESC LIMIT 1), 0)"""


def _fetch_all(sql, args=()):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def _fetch_one(sql, args=()):
    with get_db().cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()


def _write(sql, args=()):
    """Run an INSERT/UPDATE, commit, and return (lastrowid, rowcount)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, args)
        result = (cur.lastrowid, cur.rowcount)
    db.commit()
    return result


# ---------- users ----------

def get_user_by_email(email):
    return _fetch_one("SELECT * FROM users WHERE email = %s", (email,))


# ---------- stops ----------

def stop_exists(stop_id):
    return _fetch_one("SELECT 1 FROM stops WHERE stop_id = %s", (stop_id,)) is not None


def list_stop_choices():
    """Stop id and name for form drop-downs."""
    return _fetch_all("SELECT stop_id, name FROM stops ORDER BY name")


def list_stops(route_id=None, limit=10, offset=0):
    sql = ("SELECT s.*, r.name AS route_name FROM stops s "
           "LEFT JOIN routes r ON s.route_id = r.route_id")
    args = []
    if route_id:
        sql += " WHERE s.route_id = %s"
        args.append(route_id)
    sql += " ORDER BY s.name LIMIT %s OFFSET %s"
    args += [limit, offset]
    return _fetch_all(sql, args)


def get_stop(stop_id):
    """One stop with its evidence counts (for ETA and confidence)."""
    return _fetch_one(f"""
        SELECT s.*, r.name AS route_name,
               {_STOP_CONFIRMS} AS pin_reports, {_ACTIVE_TAXIS} AS gps_confirms
        FROM stops s LEFT JOIN routes r ON s.route_id = r.route_id
        WHERE s.stop_id = %s
    """, (stop_id,))


def get_stop_id_by_name(name):
    row = _fetch_one("SELECT stop_id FROM stops WHERE name = %s", (name,))
    return row["stop_id"] if row else None


def create_stop(name, route_id=None, distance_km=None, latitude=None, longitude=None):
    stop_id, _ = _write(
        "INSERT INTO stops (name, route_id, distance_to_cbd_km, latitude, longitude) "
        "VALUES (%s, %s, %s, %s, %s)",
        (name, route_id, distance_km, latitude, longitude),
    )
    return stop_id


def update_stop(stop_id, fields):
    """fields: dict limited to name / distance_to_cbd_km. Returns False if no such stop."""
    if not stop_exists(stop_id):
        return False
    allowed = {k: v for k, v in fields.items() if k in ("name", "distance_to_cbd_km")}
    # Column names come only from the fixed allow-list above; values stay parameters.
    sets = ", ".join(f"{col} = %s" for col in allowed)
    _write(f"UPDATE stops SET {sets} WHERE stop_id = %s", (*allowed.values(), stop_id))
    return True


def route_exists(route_id):
    return _fetch_one("SELECT 1 FROM routes WHERE route_id = %s", (route_id,)) is not None


def stops_with_evidence():
    """Every stop with route name, distance and evidence counts (Live Stops page)."""
    return _fetch_all(f"""
        SELECT s.stop_id, s.name, r.name AS route, s.distance_to_cbd_km,
               {_STOP_CONFIRMS} AS pin_reports, {_ACTIVE_TAXIS} AS gps_confirms
        FROM stops s LEFT JOIN routes r ON s.route_id = r.route_id
        ORDER BY s.name
    """)


def stops_with_demand():
    """Every stop with its latest waiting count and active taxis (heat map)."""
    return _fetch_all(f"""
        SELECT s.stop_id, s.name, s.latitude, s.longitude,
               {_LATEST_WAITING} AS waiting, {_ACTIVE_TAXIS} AS taxis
        FROM stops s ORDER BY s.name
    """)


# ---------- demand reports ----------

def create_demand_report(stop_id, waiting, reported_by=None):
    report_id, _ = _write(
        "INSERT INTO demand_reports (stop_id, waiting_passengers, reported_by) VALUES (%s, %s, %s)",
        (stop_id, waiting, reported_by),
    )
    return report_id


def list_demand_reports(stop_id=None, limit=10, offset=0):
    sql = ("SELECT dr.*, s.name AS stop_name FROM demand_reports dr "
           "JOIN stops s ON dr.stop_id = s.stop_id")
    args = []
    if stop_id:
        sql += " WHERE dr.stop_id = %s"
        args.append(stop_id)
    sql += " ORDER BY dr.reported_at DESC, dr.report_id DESC LIMIT %s OFFSET %s"
    args += [limit, offset]
    return _fetch_all(sql, args)


def get_demand_report(report_id):
    return _fetch_one("SELECT * FROM demand_reports WHERE report_id = %s", (report_id,))


def recent_demand_history(limit=8):
    """Most recent waiting counts, returned oldest -> newest for forecasting."""
    rows = _fetch_all(
        "SELECT waiting_passengers FROM demand_reports "
        "ORDER BY reported_at DESC, report_id DESC LIMIT %s", (limit,))
    return [r["waiting_passengers"] for r in rows][::-1]


# ---------- taxi positions ----------

def create_taxi_position(stop_id, seats_available, driver_id=None):
    position_id, _ = _write(
        "INSERT INTO taxi_positions (stop_id, driver_id, seats_available, is_active) "
        "VALUES (%s, %s, %s, TRUE)",
        (stop_id, driver_id, seats_available),
    )
    return position_id


def get_taxi_position(position_id):
    return _fetch_one("SELECT * FROM taxi_positions WHERE position_id = %s", (position_id,))


def list_taxi_positions(active_only=True, stop_id=None):
    sql = ("SELECT tp.*, s.name AS stop_name FROM taxi_positions tp "
           "JOIN stops s ON tp.stop_id = s.stop_id WHERE 1 = 1")
    args = []
    if active_only:
        sql += " AND tp.is_active = 1"
    if stop_id:
        sql += " AND tp.stop_id = %s"
        args.append(stop_id)
    sql += " ORDER BY s.name, tp.position_id"
    return _fetch_all(sql, args)


def set_taxi_active(position_id, is_active):
    """Returns False if the taxi position does not exist."""
    if get_taxi_position(position_id) is None:
        return False
    _write("UPDATE taxi_positions SET is_active = %s WHERE position_id = %s",
           (is_active, position_id))
    return True


def check_out_taxi(position_id):
    """Check out an active taxi. Returns True if it was active."""
    _, changed = _write(
        "UPDATE taxi_positions SET is_active = FALSE WHERE position_id = %s AND is_active = 1",
        (position_id,))
    return changed > 0


def active_seat_counts():
    return [r["seats_available"] for r in
            _fetch_all("SELECT seats_available FROM taxi_positions WHERE is_active = 1")]


# ---------- problem reports ----------

def create_problem(stop_id, problem_type, description="", reported_by=None):
    problem_id, _ = _write(
        "INSERT INTO problem_reports (stop_id, problem_type, description, reported_by) "
        "VALUES (%s, %s, %s, %s)",
        (stop_id, problem_type, description, reported_by),
    )
    return problem_id


def get_problem(problem_id):
    return _fetch_one("""
        SELECT pr.*, s.name AS stop_name FROM problem_reports pr
        JOIN stops s ON pr.stop_id = s.stop_id WHERE pr.problem_id = %s
    """, (problem_id,))


def list_problems(status="open", limit=50, offset=0):
    return _fetch_all("""
        SELECT pr.*, s.name AS stop_name FROM problem_reports pr
        JOIN stops s ON pr.stop_id = s.stop_id
        WHERE pr.status = %s
        ORDER BY pr.reported_at DESC, pr.problem_id DESC LIMIT %s OFFSET %s
    """, (status, limit, offset))


def set_problem_status(problem_id, status):
    """Returns False if the problem does not exist."""
    if get_problem(problem_id) is None:
        return False
    _write("UPDATE problem_reports SET status = %s WHERE problem_id = %s", (status, problem_id))
    return True


def resolve_open_problem(problem_id):
    """Resolve an open problem. Returns True if it was open."""
    _, changed = _write(
        "UPDATE problem_reports SET status = 'resolved' WHERE problem_id = %s AND status = 'open'",
        (problem_id,))
    return changed > 0


def count_open_problems():
    return _fetch_one("SELECT COUNT(*) AS n FROM problem_reports WHERE status = 'open'")["n"]


# ---------- verification reports ----------

def create_verification(stop_id, report_type, safety_rating, reported_by=None):
    verification_id, _ = _write(
        "INSERT INTO verification_reports (stop_id, report_type, safety_rating, reported_by) "
        "VALUES (%s, %s, %s, %s)",
        (stop_id, report_type, safety_rating, reported_by),
    )
    return verification_id
