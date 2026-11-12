# 🏆 APEX PREMIER LEAGUE - SPORTS LEAGUE MANAGEMENT PLATFORM

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/nksingh2013/sports-league-platform)

A complete, modern, database-connected Sports League Management Platform built with **Python Flask**, **SQLite**, **Vanilla JavaScript**, and high-performance **HTML5/CSS3** responsive styling.

Inspired by premier digital sports platforms (**ESPN**, **FIFA**, **Premier League**, and modern sports analytics dashboards), the system delivers a stadium-inspired dark navy aesthetic, electric green accents, fluid sports animations, and a secure relational management back-office.

---

## ⚡ 1. KEY FEATURES

### 🌐 Public Experience
- **Home Dashboard (`/`)**: Stadium floodlight hero section, animated 3D soccer ball with realistic rotation and ground pedestal, animated statistical counters, live match marquee with pulsating beacons, upcoming fixtures, latest results, championship table snippet, and Golden Boot race.
- **Standings & Points Table (`/standings`)**: Dynamically computed table (Played, Won, Drawn, Lost, Goals For, Goals Against, Goal Difference, Points, and Last 5 Match Form guide `[W, D, L]`). Supports Champions League, Continental, and Relegation zone color-coding.
- **Clubs Directory (`/teams`)**: Card grid of all 8 clubs with coach, founded year, venue, squad size, live search filter, and individual club profiles (`/team/<id>`).
- **Team Detail Profiles (`/team/<id>`)**: Comprehensive club hub with official crest, coach profile, stadium capacity, squad roster segmented by position, and historical match logs.
- **Player Leaderboard & Roster (`/players`)**: High-res player cards with positions, nationality, jersey number, goals, assists, matches, and clean sheets. Multi-dimensional filtering by club, position, search query, and sorting.
- **Fixtures & Schedule (`/fixtures`)**: Schedule of upcoming matches with filtering by team, venue, and status.
- **Match Results (`/results`)**: Final certified scorelines, match summaries, and winner highlights.
- **Venues & Stadiums (`/venues`)**: Stadium directory detailing spectator capacities, turf surfaces, cities, and match counts.
- **Season Analytics (`/statistics`)**: Golden Boot leaders, top playmakers (assists), safe hands (goalkeepers), top attacking clubs, and best defenses.

### 🛡️ Secure Admin Control Panel
- **Protected Routes (`/admin/*`)**: Session authentication guarded by `@admin_required` decorators and Werkzeug password hashing.
- **Dashboard Overview (`/admin/dashboard`)**: Metric overview tiles, quick-action shortcuts, recent activity, and top table snapshot.
- **Manage Teams (`/admin/teams`)**: Full CRUD (Create, Read, Edit, Delete) for clubs with venue assignment and brand color customization.
- **Manage Players (`/admin/players`)**: Full CRUD for players with jersey number validation, positions, and performance stats.
- **Manage Fixtures (`/admin/fixtures`)**: Schedule new matches with date/time pickers, prevent duplicate team scheduling, and assign venues.
- **Scorekeeping & Results (`/admin/results`)**: Record and certify match scorelines, live minute markers, and match summaries. **Automatically recalculates the league standings, goal differences, and form records in real-time.**
- **Manage Venues (`/admin/venues`)**: Stadium CRUD management.
- **Manage Seasons (`/admin/seasons`)**: Multi-season tournament support with single-click active season switching.

### 🔄 REST API Endpoints
- `GET /api/standings`: Returns full computed league standings with form guide.
- `GET /api/teams`: Returns list of all clubs.
- `GET /api/players`: Returns players list, filterable by `?team_id=X`.
- `GET /api/fixtures`: Returns all fixtures.
- `GET /api/search?q=query`: Live cross-entity search for clubs and athletes.

---

## 🎨 2. SPORTS ANIMATIONS & UI/UX

1. **Animated 3D Soccer Ball**: Interactive CSS 3D sphere in the hero section with pentagonal leather patches, natural wobble, mouse parallax, and ground shadow breathing.
2. **Stadium Floodlight Glow**: Conic-gradient floodlight beams with smooth atmospheric pulse simulation.
3. **Animated Numbers (Count-Up)**: Numerical counters ease smoothly from 0 to target metrics upon scroll reveal.
4. **Card 3D Hover Tilt**: Club and player cards compute cursor coordinates to apply dynamic perspective 3D rotation and neon electric green border illumination.
5. **Pulsing Match Status Indicators**: High-visibility glowing red badge for in-progress live games and cyan for upcoming fixtures.
6. **Mobile Table Stacking**: Data tables automatically convert to responsive stacked cards on mobile devices (tested down to 375px), preventing unwanted horizontal viewport overflow.
7. **Accessibility (`prefers-reduced-motion`)**: Fully respects user system animation preferences.

---

## 🗄️ 3. DATABASE SCHEMA & RELATIONSHIPS

The platform uses **SQLite** with Foreign Key constraints enabled (`PRAGMA foreign_keys = ON;`).

```
   +-------------+       1:N       +-------------+
   |   venues    | <-------------- |    teams    |
   +-------------+                 +-------------+
          ^                               | 1:N
          |                               v
          | 1:N                    +-------------+
          |                        |   players   |
          |                        +-------------+
   +-------------+                        |
   |   matches   | >----------------------+ (home_team_id, away_team_id)
   +-------------+
          ^
          | N:1
   +-------------+
   |   seasons   |
   +-------------+
```

### Table Definitions:
- **`admins`**: Administrator credentials with hashed passwords (`password_hash`), usernames, and roles.
- **`seasons`**: Tournament seasons (`is_active` boolean flag, start/end dates).
- **`venues`**: Stadium metadata (capacity, city, surface, photo URL).
- **`teams`**: Club identity (name, code, coach, logo, primary/secondary brand colors, home venue foreign key).
- **`players`**: Athlete records linked to `team_id` (ON DELETE CASCADE), jersey number (unique per team), position check constraint, and stats.
- **`matches`**: Fixtures connecting `season_id`, `home_team_id`, `away_team_id`, `venue_id`, scores, minute, and status (`scheduled`, `live`, `completed`, `postponed`).

---

## 🚀 4. INSTALLATION & SETUP

### Prerequisites
- Python 3.10+ installed

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Seed the Database
Populates 8 clubs, 40 players, 4 stadiums, 1 active season, and 15 fixtures (completed, live, and scheduled):
```bash
python seed.py
```

### Step 3: Start the Application
```bash
python app.py
```
Open your browser at:
`http://localhost:5000`

---

## 🔑 5. DEFAULT ADMINISTRATOR CREDENTIALS

The seed script automatically provisions the initial administrative user:

- **Login URL**: `http://localhost:5000/login`
- **Username / Email**: `admin@sportsleague.com`
- **Password**: `Admin@2026!`

*(Passwords are hashed with Werkzeug secure salted hashing; never stored in plaintext).*

---

## 📱 6. RESPONSIVE DESIGN BREAKPOINTS TESTED

- **Desktop (1440px+)**: Wide stadium layouts, 4-column metric counters, full data tables with sticky headers.
- **Laptop (1024px)**: 2-column dashboard splits, 3-column team cards.
- **Tablet (768px)**: Collapsible admin sidebar, flexible fixture scoreboards.
- **Mobile (430px & 375px)**: Compact mobile header with hamburger menu, stacked table card conversions, touch-friendly tap targets.
