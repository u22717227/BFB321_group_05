# Eyabantu Taxi Program

**BFB 321 Group 05**
Real-time visibility for South Africa's minibus taxi industry: live stops with ETA and confidence, a demand heat map with a taxi deployment plan, problem reports, and crowdsourced stop verification.

## Tech stack
- **Frontend:** HTML and CSS, rendered by Flask with Jinja2 templates
- **Backend:** Python 3 and Flask, with a REST API blueprint returning JSON
- **Database:** MySQL 8 (accessed with PyMySQL; all queries are parameterised)
- **Supply chain model:** `supply_chain_model.py` (ETA, demand intensity, deployment, confidence, forecast, occupancy)
- **Testing:** pytest

## Setup (local MySQL)

You need Python 3.10+ and MySQL Server 8 running locally.

1. **Clone the repo**
   ```bash
   git clone https://github.com/u22717227/BFB321_group_05.git
   cd BFB321_group_05
   ```
   The folder name after `cd` must match the repository name on GitHub.

2. **Create a virtual environment and install packages**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create your `.env` file**
   ```bash
   copy .env.example .env     # Windows
   cp .env.example .env       # Mac/Linux
   ```
   Open `.env` and set `DB_USER` and `DB_PASSWORD` to your MySQL login (usually `root` and the password you use in MySQL Workbench).

4. **Create the database and load the sample data (one command)**
   ```bash
   mysql -u root -p -e "source schema.sql; source seed.sql"
   ```
   This command works in PowerShell, Command Prompt, Mac and Linux. Alternatively, open `schema.sql` and then `seed.sql` in MySQL Workbench and run each with the lightning-bolt button.

5. **Run the app**
   ```bash
   python app.py
   # or: flask --app app run
   ```
   Open http://127.0.0.1:5000

### Demo accounts
All three accounts use the password `demo123`.

| Email | Role | Can do |
|-------|------|--------|
| `commuter@eyabantu.co.za` | Commuter | View stops and demand, report demand, problems and stops |
| `driver@eyabantu.co.za` | Driver | Everything a commuter can, plus taxi check-in and check-out |
| `assoc@eyabantu.co.za` | Taxi association | Everything a driver can, plus resolve problems |

## Pages

| Page | URL | What it does | Login needed |
|------|-----|--------------|--------------|
| Home | `/` | Live KPI dashboard and links to each user type's pages | No |
| Live stops | `/stops` | Every stop with ETA, confidence (Verified / Unverified), safety rating, and open problems | No |
| Demand | `/demand` | Demand heat map (intensity and level per stop) and the taxi deployment plan | No |
| Report a stop | `/report` | Confirm a stop, a safe pickup, or rate safety | No |
| Login / Logout | `/login`, `/logout` | Sign in with a demo account | — |

### Form actions (HTML form posts)
Each form saves to MySQL, redirects back to the page, and shows a green or red message.

| Action | Route | Login needed |
|--------|-------|--------------|
| Report waiting passengers | `POST /demand/report` | No |
| Report a problem | `POST /problems/report` | No |
| Resolve a problem | `POST /problems/<id>/resolve` | Association |
| Taxi check-in | `POST /taxis/checkin` | Driver or association |
| Taxi check-out | `POST /taxis/<id>/checkout` | Driver or association |
| Submit a stop report | `POST /report` | No |

### End-to-end test checklist
1. Home page shows 8 KPIs (7 stops and 14.3% verified with the seed data).
2. Demand: report waiting passengers. The heat map updates.
3. Log in as `assoc@eyabantu.co.za`.
4. Live stops: resolve the open problem, then report a new one.
5. Demand: check a taxi in, then check it out.
6. Report a stop: submit the form.

To reset the data, run the command in step 4 of the setup again.

## Home-page KPIs

| KPI | How it is calculated |
|-----|----------------------|
| Taxi stops | Number of rows in `stops` |
| Stops verified (%) | Stops with confidence ≥ 0.5, divided by all stops. Confidence = (stop confirmations + 2 × active taxis) ÷ 10, capped at 1, and capped at 0.5 below 3 pieces of evidence |
| Open problems | Problem reports with status `open` |
| Active taxis | Taxi check-ins with `is_active` = true |
| Under-served stops | Stops where demand intensity > 1. Intensity = latest waiting passengers ÷ (active taxis × 15 seats) |
| Average waiting passengers | Mean of the latest waiting count at each stop |
| Forecast next demand | Exponential smoothing (α = 0.3) over the 8 most recent demand reports, oldest to newest |
| Average taxi occupancy | Mean of (15 − seats available) ÷ 15 over active taxis |

Demand levels on the heat map: above 3 = Very high, 1.1–3 = High, 0.8–1.1 = Moderate, below 0.8 = Low. A stop with people waiting and no taxis is Very high; a stop with nobody waiting is Low.

## REST API endpoints

All endpoints are under `/api` and return JSON.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/stops?route_id=&page=&size=` | List stops (paginated, optional route filter; `size` max 50) |
| GET | `/api/stops/<id>` | Single stop with ETA and confidence |
| POST | `/api/stops` | Create a stop (`name` required; `route_id`, `distance_to_cbd_km`, `latitude`, `longitude` optional) |
| PATCH | `/api/stops/<id>` | Update a stop's name or distance to CBD |
| GET | `/api/demand-reports?stop_id=&page=&size=` | List demand reports, newest first (paginated, optional stop filter) |
| GET | `/api/demand-reports/<id>` | Single demand report |
| POST | `/api/demand-reports` | Report waiting passengers |
| GET | `/api/heatmap` | Heat-map data with intensity and level per stop |
| GET | `/api/taxi-positions?active=&stop_id=` | List taxi check-ins (active only unless `active=false`) |
| GET | `/api/taxi-positions/<id>` | Single taxi check-in |
| POST | `/api/taxi-positions` | Driver check-in |
| PATCH | `/api/taxi-positions/<id>` | Check a taxi out or back in (`{"is_active": false}`) |
| GET | `/api/problems?status=open&page=&size=` | List problems (paginated, filter by `open` or `resolved`) |
| GET | `/api/problems/<id>` | Single problem |
| POST | `/api/problems` | Report a problem |
| PATCH | `/api/problems/<id>` | Resolve or reopen a problem |

### Example requests and responses

```json
POST /api/stops
{"name": "Hatfield", "route_id": 1, "distance_to_cbd_km": 4.2}

201 Created
{"stop_id": 8}
```

```json
POST /api/demand-reports
{"stop_id": 1, "waiting_passengers": 40}

201 Created
{"report_id": 12}
```

```json
POST /api/taxi-positions
{"stop_id": 3, "seats_available": 10}

201 Created
{"position_id": 4}
```

```json
PATCH /api/problems/1
{"status": "resolved"}

200 OK
{"ok": true}
```

```json
GET /api/stops?route_id=1&page=1&size=3

200 OK
{"page": 1, "size": 3, "items": [ ... ]}
```

### Error responses
Errors return JSON in the form `{"error": "message"}`.

| Status | When |
|--------|------|
| 400 Bad Request | Missing or invalid fields (for example `waiting_passengers` outside 0–1000, or `seats_available` outside 0–15) |
| 404 Not Found | The stop, problem or taxi position does not exist |
| 409 Conflict | Duplicate data (for example renaming a stop to a name already used on its route) |
| 500 Internal Server Error | Unexpected error; the database change is rolled back and the error is written to `eyabantu.log` |

## Schema
Seven related tables. Primary keys, foreign keys, CHECK constraints, audit fields and indexes are in [schema.sql](schema.sql).

![ERD](docs/erd.png)

| Table | Purpose | Key relationships |
|-------|---------|-------------------|
| `users` | Commuters, drivers and taxi associations (`role`) | One user files many reports and taxi positions |
| `routes` | The 6 pilot routes into Pretoria CBD | One route has many stops |
| `stops` | Taxi stops with distance to CBD and coordinates | Belongs to a route; has many reports and positions |
| `taxi_positions` | Driver check-ins (`is_active`, `seats_available`) | Many per stop; many per driver |
| `demand_reports` | Waiting passengers at a stop | Many per stop |
| `problem_reports` | Problems at ranks, `open` or `resolved` | Many per stop |
| `verification_reports` | Crowdsourced stop confirmations and safety ratings | Many per stop |

Indexes: `(stop_id, is_active)` on `taxi_positions`, `(stop_id, reported_at)` on `demand_reports`, `(stop_id, status)` on `problem_reports`.

## Project structure
```
app.py                  App factory: config, logging, blueprints, error handlers
models.py               All database queries (one function per operation, table names match the ERD)
routes/pages.py         Page routes, form actions and login (pages blueprint)
routes/api.py           REST API blueprint mounted at /api
config.py               Development / testing / production settings, chosen by APP_ENV in .env
db.py                   One MySQL connection per request, closed on teardown
supply_chain_model.py   ETA, demand intensity and level, heat map, deployment, confidence, forecast, occupancy
schema.sql              Drops and recreates the eyabantu database (tables, keys, constraints, indexes)
seed.sql                Sample data for every table, including the demo accounts
templates/              Jinja2 pages, all extending base.html (navigation and flash messages)
static/                 style.css and images
docs/erd.png            Entity relationship diagram (source: docs/erd.mmd)
tests/                  pytest tests for supply_chain_model.py
pytest.ini              Lets pytest find the project modules
requirements.txt        Python packages
.env.example            Template for .env (the real .env is in .gitignore)
```

## Configuration
Settings are read from `.env` (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development`, `testing` or `production` (production turns debug off) |
| `SECRET_KEY` | Signs login sessions; use a long random string |
| `DB_HOST`, `DB_PORT` | MySQL server (default `localhost`, `3306`) |
| `DB_USER`, `DB_PASSWORD` | MySQL login |
| `DB_NAME` | Database name (`eyabantu`) |

## Backup, restore and rollback
```bash
mysqldump -u root -p eyabantu > backup.sql
mysql -u root -p eyabantu -e "source backup.sql"
```

Rollback: restore the latest `backup.sql`. To reset from scratch, run `schema.sql` (it drops and recreates the database) and then `seed.sql`.

## Testing
```bash
pytest
```
Runs the model tests in `tests/` (`pytest.ini` sets the import path). Use the end-to-end checklist above to test the pages and forms.

## Notes
- Demo passwords are stored as Werkzeug password hashes, never as plain text.
- Logging goes to `eyabantu.log`.
- Code is split into three layers: routes (`routes/`) handle requests, `models.py` talks to MySQL, and `supply_chain_model.py` does the calculations. Routes never contain SQL.
- All supply chain calculations come from `supply_chain_model.py`, so the pages and the API always use the same rules.

## Team (Group 05)

Eyabantu Taxi Program. Group 05: Harley Dalmeida, Jaco Grobbelaar and Danie Smit.

| Name | Student number | GitHub username |
|------|----------------|-----------------|
| Harley Dalmeida | u22717227 | [u22717227](https://github.com/u22717227) |
| Jaco Grobbelaar | u23535173 | [jaco-06](https://github.com/jaco-06) |
| Danie Smit | u23596717 | [u23596717-Danie-Smit](https://github.com/u23596717-Danie-Smit) |

## Task allocation

| Member | Work |
|--------|------|
| Harley Dalmeida | Flask app setup (`app.py`), role-based login, MySQL connection (`config.py`, `db.py`, `.env.example`), `schema.sql`, `seed.sql`, the database layer in `models.py`, and the REST API in `routes/api.py` |
| Jaco Grobbelaar | Page templates (`base`, welcome, live stops, demand, report, login), shared CSS and navigation, the page routes in `routes/pages.py`, and the HTML forms for demand reports, problem reports, resolve, and taxi check-in and check-out |
| Danie Smit | Supply chain calculations in `supply_chain_model.py` (ETA, demand intensity, heat map, deployment, confidence, forecast, occupancy), home-page KPIs, pytest tests, the ERD, and the README |
