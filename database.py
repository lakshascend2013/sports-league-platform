import sqlite3
import os
from flask import g, current_app

def get_db():
    """Get database connection for the current request context."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        # Ensure instance directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable Foreign Key enforcement
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection if open."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize database from schema.sql."""
    if app:
        with app.app_context():
            db = get_db()
            with open(os.path.join(current_app.config['BASE_DIR'], 'schema.sql'), 'r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
    else:
        db = get_db()
        with open(os.path.join(current_app.config['BASE_DIR'], 'schema.sql'), 'r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()

def calculate_standings(season_id=None):
    """
    Dynamically calculate the league standings from completed matches.
    Sorts by:
      1. Points (DESC)
      2. Goal Difference (DESC)
      3. Goals For (DESC)
      4. Wins (DESC)
      5. Team Name (ASC)
    Includes last 5 match form guide (W, D, L).
    """
    db = get_db()
    
    # If no season_id is passed, get active season
    if season_id is None:
        active_season = db.execute("SELECT id FROM seasons WHERE is_active = 1 LIMIT 1").fetchone()
        if active_season:
            season_id = active_season['id']
        else:
            first_season = db.execute("SELECT id FROM seasons ORDER BY id ASC LIMIT 1").fetchone()
            season_id = first_season['id'] if first_season else None

    # Fetch all teams
    teams = db.execute("SELECT id, name, short_name, code, logo_url, primary_color FROM teams ORDER BY name ASC").fetchall()
    
    standings_map = {}
    for team in teams:
        standings_map[team['id']] = {
            'team_id': team['id'],
            'name': team['name'],
            'short_name': team['short_name'],
            'code': team['code'],
            'logo_url': team['logo_url'],
            'primary_color': team['primary_color'],
            'played': 0,
            'won': 0,
            'drawn': 0,
            'lost': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'points': 0,
            'form': [],  # list of {'result': 'W'|'D'|'L', 'score': '2-1', 'opponent': 'XYZ'}
            'win_rate': 0.0
        }

    if season_id is not None:
        # Fetch completed matches in chronological order
        matches = db.execute("""
            SELECT m.id, m.home_team_id, m.away_team_id, m.home_score, m.away_score, 
                   m.match_date, m.match_time,
                   ht.short_name as home_name, at.short_name as away_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            WHERE m.season_id = ? AND m.status = 'completed'
            ORDER BY m.match_date ASC, m.match_time ASC
        """, (season_id,)).fetchall()

        for m in matches:
            hid = m['home_team_id']
            aid = m['away_team_id']
            hs = m['home_score']
            as_score = m['away_score']

            if hid in standings_map and aid in standings_map:
                ht = standings_map[hid]
                at = standings_map[aid]

                ht['played'] += 1
                at['played'] += 1
                ht['goals_for'] += hs
                ht['goals_against'] += as_score
                at['goals_for'] += as_score
                at['goals_against'] += hs

                if hs > as_score:
                    # Home Win
                    ht['won'] += 1
                    ht['points'] += 3
                    ht['form'].append({'result': 'W', 'score': f"{hs}-{as_score}", 'opponent': m['away_name'], 'is_home': True})
                    
                    at['lost'] += 1
                    at['form'].append({'result': 'L', 'score': f"{as_score}-{hs}", 'opponent': m['home_name'], 'is_home': False})
                elif hs < as_score:
                    # Away Win
                    at['won'] += 1
                    at['points'] += 3
                    at['form'].append({'result': 'W', 'score': f"{as_score}-{hs}", 'opponent': m['home_name'], 'is_home': False})
                    
                    ht['lost'] += 1
                    ht['form'].append({'result': 'L', 'score': f"{hs}-{as_score}", 'opponent': m['away_name'], 'is_home': True})
                else:
                    # Draw
                    ht['drawn'] += 1
                    ht['points'] += 1
                    ht['form'].append({'result': 'D', 'score': f"{hs}-{as_score}", 'opponent': m['away_name'], 'is_home': True})
                    
                    at['drawn'] += 1
                    at['points'] += 1
                    at['form'].append({'result': 'D', 'score': f"{as_score}-{hs}", 'opponent': m['home_name'], 'is_home': False})

    # Compute goal diff, win rate, slice last 5 form matches
    standings_list = list(standings_map.values())
    for item in standings_list:
        item['goal_difference'] = item['goals_for'] - item['goals_against']
        if item['played'] > 0:
            item['win_rate'] = round((item['won'] / item['played']) * 100, 1)
        else:
            item['win_rate'] = 0.0
        # Keep last 5 matches (reverse so most recent is first, or keep last 5 chronological)
        item['form_last5'] = item['form'][-5:]

    # Sort
    standings_list.sort(key=lambda x: (
        -x['points'],
        -x['goal_difference'],
        -x['goals_for'],
        -x['won'],
        x['name'].lower()
    ))

    # Add position and zone flags
    total_teams = len(standings_list)
    for idx, item in enumerate(standings_list, start=1):
        item['position'] = idx
        if idx == 1:
            item['zone'] = 'champion'
            item['zone_title'] = 'Leader / Championship'
        elif idx in (2, 3, 4):
            item['zone'] = 'continental'
            item['zone_title'] = 'Continental Cup'
        elif total_teams >= 6 and idx > total_teams - 2:
            item['zone'] = 'relegation'
            item['zone_title'] = 'Relegation Zone'
        else:
            item['zone'] = 'mid-table'
            item['zone_title'] = 'Mid Table'

    return standings_list
