import os
import functools
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, jsonify, g, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import get_db, close_db, init_db, calculate_standings

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['BASE_DIR'] = Config.BASE_DIR

    # Register teardown
    app.teardown_appcontext(close_db)

    # Context processor to inject global variables in templates
    @app.context_processor
    def inject_globals():
        db = get_db()
        active_season = db.execute("SELECT * FROM seasons WHERE is_active = 1 LIMIT 1").fetchone()
        seasons_list = db.execute("SELECT * FROM seasons ORDER BY year DESC").fetchall()
        return {
            'league_name': Config.LEAGUE_NAME,
            'league_tagline': Config.LEAGUE_TAGLINE,
            'current_year': Config.LEAGUE_SEASON_CURRENT,
            'active_season': active_season,
            'all_seasons': seasons_list,
            'is_admin': 'admin_id' in session,
            'admin_username': session.get('admin_username', ''),
            'admin_name': session.get('admin_name', '')
        }

    # Auto-initialize and seed database on first launch (e.g. Render deployment)
    with app.app_context():
        try:
            db = get_db()
            table_check = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='teams'").fetchone()
            if not table_check:
                from seed import seed_database
                seed_database()
        except Exception as e:
            app.logger.warning(f"Auto-init notice: {e}")

    # Custom Jinja filters
    @app.template_filter('format_date')
    def format_date(value, format_str='%b %d, %Y'):
        if not value:
            return ''
        try:
            if isinstance(value, str):
                dt = datetime.strptime(value, '%Y-%m-%d')
            else:
                dt = value
            return dt.strftime(format_str)
        except Exception:
            return str(value)

    @app.template_filter('format_time')
    def format_time(value):
        if not value:
            return ''
        try:
            # Matches HH:MM or HH:MM:SS
            parts = str(value).split(':')
            hour = int(parts[0])
            minute = parts[1]
            suffix = "PM" if hour >= 12 else "AM"
            h12 = hour % 12
            if h12 == 0:
                h12 = 12
            return f"{h12}:{minute} {suffix}"
        except Exception:
            return str(value)

    # -------------------------------------------------------------
    # Authentication Helper Decorator
    # -------------------------------------------------------------
    def admin_required(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if 'admin_id' not in session:
                flash("Access denied. Please log in with administrator credentials.", "warning")
                return redirect(url_for('login', next=request.path))
            return view(**kwargs)
        return wrapped_view

    # -------------------------------------------------------------
    # PUBLIC ROUTES
    # -------------------------------------------------------------
    @app.route('/')
    def index():
        db = get_db()
        standings = calculate_standings()
        
        # Aggregate stats
        total_teams = db.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        total_players = db.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        total_matches = db.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        total_goals = db.execute("SELECT (SUM(home_score) + SUM(away_score)) FROM matches WHERE status = 'completed'").fetchone()[0] or 0
        
        # Live matches
        live_matches = db.execute("""
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo, ht.primary_color as home_color,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo, at.primary_color as away_color,
                   v.name as venue_name, v.city as venue_city
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.status = 'live'
            ORDER BY m.match_date ASC, m.match_time ASC
        """).fetchall()

        # Upcoming 4 fixtures
        upcoming_matches = db.execute("""
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo, ht.primary_color as home_color,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo, at.primary_color as away_color,
                   v.name as venue_name, v.city as venue_city
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.status = 'scheduled'
            ORDER BY m.match_date ASC, m.match_time ASC
            LIMIT 4
        """).fetchall()

        # Recent 4 completed results
        recent_results = db.execute("""
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo, ht.primary_color as home_color,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo, at.primary_color as away_color,
                   v.name as venue_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.status = 'completed'
            ORDER BY m.match_date DESC, m.match_time DESC
            LIMIT 4
        """).fetchall()

        # Top 5 players (Golden Boot)
        top_scorers = db.execute("""
            SELECT p.*, t.name as team_name, t.short_name as team_short, t.logo_url as team_logo
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.goals DESC, p.assists DESC
            LIMIT 5
        """).fetchall()

        return render_template(
            'index.html',
            standings=standings[:5],  # top 5 on dashboard
            total_teams=total_teams,
            total_players=total_players,
            total_matches=total_matches,
            total_goals=total_goals,
            live_matches=live_matches,
            upcoming_matches=upcoming_matches,
            recent_results=recent_results,
            top_scorers=top_scorers
        )

    @app.route('/teams')
    def teams():
        db = get_db()
        search_query = request.args.get('q', '').strip()
        
        sql = """
            SELECT t.*, v.name as venue_name, v.city as venue_city,
                   COUNT(p.id) as player_count
            FROM teams t
            LEFT JOIN venues v ON t.home_venue_id = v.id
            LEFT JOIN players p ON t.id = p.team_id
        """
        params = []
        if search_query:
            sql += " WHERE t.name LIKE ? OR t.short_name LIKE ? OR t.coach LIKE ?"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
        
        sql += " GROUP BY t.id ORDER BY t.name ASC"
        teams_list = db.execute(sql, params).fetchall()

        # Merge standings statistics for each team
        standings = {s['team_id']: s for s in calculate_standings()}
        enriched_teams = []
        for t in teams_list:
            s_data = standings.get(t['id'], {
                'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 
                'goals_for': 0, 'goals_against': 0, 'points': 0, 'position': '-'
            })
            enriched_teams.append({**dict(t), **s_data})

        return render_template('teams.html', teams=enriched_teams, search_query=search_query)

    @app.route('/team/<int:team_id>')
    def team_profile(team_id):
        db = get_db()
        team = db.execute("""
            SELECT t.*, v.name as venue_name, v.city as venue_city, v.capacity as venue_capacity
            FROM teams t
            LEFT JOIN venues v ON t.home_venue_id = v.id
            WHERE t.id = ?
        """, (team_id,)).fetchone()

        if not team:
            flash("Team not found.", "danger")
            return redirect(url_for('teams'))

        # Roster
        roster = db.execute("""
            SELECT * FROM players WHERE team_id = ? 
            ORDER BY 
                CASE position 
                    WHEN 'Goalkeeper' THEN 1 
                    WHEN 'Defender' THEN 2 
                    WHEN 'Midfielder' THEN 3 
                    WHEN 'Forward' THEN 4 
                    ELSE 5 
                END, jersey_number ASC
        """, (team_id,)).fetchall()

        # Standings row
        standings = calculate_standings()
        team_standings = next((s for s in standings if s['team_id'] == team_id), None)

        # Recent and upcoming matches for this team
        team_matches = db.execute("""
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo,
                   v.name as venue_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.home_team_id = ? OR m.away_team_id = ?
            ORDER BY m.match_date DESC, m.match_time DESC
        """, (team_id, team_id)).fetchall()

        return render_template(
            'team_detail.html',
            team=team,
            roster=roster,
            team_standings=team_standings,
            matches=team_matches
        )

    @app.route('/players')
    def players():
        db = get_db()
        team_id = request.args.get('team_id', type=int)
        position = request.args.get('position', '').strip()
        search_query = request.args.get('q', '').strip()
        sort_by = request.args.get('sort', 'goals').strip()

        sql = """
            SELECT p.*, t.name as team_name, t.short_name as team_short, t.logo_url as team_logo, t.primary_color
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE 1=1
        """
        params = []
        if team_id:
            sql += " AND p.team_id = ?"
            params.append(team_id)
        if position:
            sql += " AND p.position = ?"
            params.append(position)
        if search_query:
            sql += " AND (p.name LIKE ? OR p.nationality LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        # Sorting logic
        if sort_by == 'assists':
            sql += " ORDER BY p.assists DESC, p.goals DESC"
        elif sort_by == 'matches':
            sql += " ORDER BY p.matches_played DESC, p.goals DESC"
        elif sort_by == 'clean_sheets':
            sql += " ORDER BY p.clean_sheets DESC, p.matches_played DESC"
        elif sort_by == 'name':
            sql += " ORDER BY p.name ASC"
        else: # goals default
            sql += " ORDER BY p.goals DESC, p.assists DESC, p.matches_played ASC"

        players_list = db.execute(sql, params).fetchall()
        teams_list = db.execute("SELECT id, name FROM teams ORDER BY name ASC").fetchall()

        return render_template(
            'players.html',
            players=players_list,
            teams=teams_list,
            selected_team=team_id,
            selected_position=position,
            search_query=search_query,
            sort_by=sort_by
        )

    @app.route('/fixtures')
    def fixtures():
        db = get_db()
        team_id = request.args.get('team_id', type=int)
        venue_id = request.args.get('venue_id', type=int)
        status_filter = request.args.get('status', '').strip()

        sql = """
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo, ht.primary_color as home_color,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo, at.primary_color as away_color,
                   v.name as venue_name, v.city as venue_city
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE 1=1
        """
        params = []

        if status_filter:
            sql += " AND m.status = ?"
            params.append(status_filter)
        else:
            # Show scheduled and live by default
            sql += " AND m.status IN ('scheduled', 'live')"

        if team_id:
            sql += " AND (m.home_team_id = ? OR m.away_team_id = ?)"
            params.extend([team_id, team_id])

        if venue_id:
            sql += " AND m.venue_id = ?"
            params.append(venue_id)

        sql += " ORDER BY m.match_date ASC, m.match_time ASC"
        matches_list = db.execute(sql, params).fetchall()

        teams_list = db.execute("SELECT id, name FROM teams ORDER BY name ASC").fetchall()
        venues_list = db.execute("SELECT id, name FROM venues ORDER BY name ASC").fetchall()

        return render_template(
            'fixtures.html',
            matches=matches_list,
            teams=teams_list,
            venues=venues_list,
            selected_team=team_id,
            selected_venue=venue_id,
            selected_status=status_filter
        )

    @app.route('/results')
    def results():
        db = get_db()
        team_id = request.args.get('team_id', type=int)
        round_no = request.args.get('round', type=int)

        sql = """
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo, ht.primary_color as home_color,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo, at.primary_color as away_color,
                   v.name as venue_name, v.city as venue_city
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.status = 'completed'
        """
        params = []
        if team_id:
            sql += " AND (m.home_team_id = ? OR m.away_team_id = ?)"
            params.extend([team_id, team_id])
        if round_no:
            sql += " AND m.round = ?"
            params.append(round_no)

        sql += " ORDER BY m.match_date DESC, m.match_time DESC"
        results_list = db.execute(sql, params).fetchall()

        teams_list = db.execute("SELECT id, name FROM teams ORDER BY name ASC").fetchall()
        rounds_list = db.execute("SELECT DISTINCT round FROM matches WHERE status = 'completed' ORDER BY round ASC").fetchall()

        return render_template(
            'results.html',
            results=results_list,
            teams=teams_list,
            rounds=rounds_list,
            selected_team=team_id,
            selected_round=round_no
        )

    @app.route('/standings')
    def standings():
        standings_list = calculate_standings()
        return render_template('standings.html', standings=standings_list)

    @app.route('/venues')
    def venues():
        db = get_db()
        venues_list = db.execute("""
            SELECT v.*, COUNT(m.id) as match_count,
                   (SELECT COUNT(*) FROM teams WHERE home_venue_id = v.id) as tenant_count
            FROM venues v
            LEFT JOIN matches m ON v.id = m.venue_id
            GROUP BY v.id
            ORDER BY v.capacity DESC
        """).fetchall()
        return render_template('venues.html', venues=venues_list)

    @app.route('/statistics')
    def statistics():
        db = get_db()
        standings = calculate_standings()

        # Top Scorers
        top_scorers = db.execute("""
            SELECT p.*, t.name as team_name, t.short_name as team_short, t.logo_url as team_logo
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.goals DESC, p.assists DESC LIMIT 10
        """).fetchall()

        # Top Assists
        top_assists = db.execute("""
            SELECT p.*, t.name as team_name, t.short_name as team_short, t.logo_url as team_logo
            FROM players p
            JOIN teams t ON p.team_id = t.id
            ORDER BY p.assists DESC, p.goals DESC LIMIT 10
        """).fetchall()

        # Clean Sheets
        clean_sheets = db.execute("""
            SELECT p.*, t.name as team_name, t.short_name as team_short, t.logo_url as team_logo
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE p.position = 'Goalkeeper'
            ORDER BY p.clean_sheets DESC, p.matches_played DESC LIMIT 10
        """).fetchall()

        # Attack Rankings
        sorted_attack = sorted(standings, key=lambda x: -x['goals_for'])
        # Defense Rankings (least goals against among teams that played)
        sorted_defense = sorted([s for s in standings if s['played'] > 0], key=lambda x: x['goals_against'])

        return render_template(
            'statistics.html',
            top_scorers=top_scorers,
            top_assists=top_assists,
            clean_sheets=clean_sheets,
            top_attack=sorted_attack,
            top_defense=sorted_defense
        )

    # -------------------------------------------------------------
    # AUTHENTICATION ROUTES
    # -------------------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'admin_id' in session:
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            username_or_email = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            db = get_db()
            admin = db.execute(
                "SELECT * FROM admins WHERE username = ? OR email = ?",
                (username_or_email, username_or_email)
            ).fetchone()

            if admin and check_password_hash(admin['password_hash'], password):
                session.clear()
                session['admin_id'] = admin['id']
                session['admin_username'] = admin['username']
                session['admin_name'] = admin['full_name']
                session['admin_role'] = admin['role']
                flash(f"Welcome back, {admin['full_name']}! You are authenticated.", "success")
                next_url = request.args.get('next')
                return redirect(next_url or url_for('admin_dashboard'))
            else:
                flash("Invalid credentials. Please verify username/email and password.", "danger")

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash("You have been securely logged out.", "info")
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # ADMIN CONTROL PANEL ROUTES (PROTECTED)
    # -------------------------------------------------------------
    @app.route('/admin')
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        db = get_db()
        counts = {
            'teams': db.execute("SELECT COUNT(*) FROM teams").fetchone()[0],
            'players': db.execute("SELECT COUNT(*) FROM players").fetchone()[0],
            'matches': db.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
            'venues': db.execute("SELECT COUNT(*) FROM venues").fetchone()[0],
            'completed': db.execute("SELECT COUNT(*) FROM matches WHERE status = 'completed'").fetchone()[0],
            'live': db.execute("SELECT COUNT(*) FROM matches WHERE status = 'live'").fetchone()[0],
            'scheduled': db.execute("SELECT COUNT(*) FROM matches WHERE status = 'scheduled'").fetchone()[0],
        }

        recent_matches = db.execute("""
            SELECT m.*, ht.short_name as home_short, at.short_name as away_short
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            ORDER BY m.id DESC LIMIT 5
        """).fetchall()

        standings = calculate_standings()[:5]

        return render_template(
            'admin/dashboard.html',
            counts=counts,
            recent_matches=recent_matches,
            standings=standings
        )

    # 1. Manage Teams
    @app.route('/admin/teams', methods=['GET', 'POST'])
    @admin_required
    def admin_teams():
        db = get_db()

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            short_name = request.form.get('short_name', '').strip()
            code = request.form.get('code', '').strip().upper()
            coach = request.form.get('coach', '').strip()
            founded_year = request.form.get('founded_year', type=int)
            home_venue_id = request.form.get('home_venue_id', type=int) or None
            primary_color = request.form.get('primary_color', '#00ff87')
            secondary_color = request.form.get('secondary_color', '#0a192f')
            logo_url = request.form.get('logo_url', '').strip() or 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=300&q=80'
            bio = request.form.get('bio', '').strip()

            if not name or not short_name or not code or not coach:
                flash("Please fill in all required team fields.", "danger")
            else:
                try:
                    db.execute("""
                        INSERT INTO teams (name, short_name, code, coach, founded_year, home_venue_id, primary_color, secondary_color, logo_url, bio)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (name, short_name, code, coach, founded_year, home_venue_id, primary_color, secondary_color, logo_url, bio))
                    db.commit()
                    flash(f"Team '{name}' was successfully registered!", "success")
                    return redirect(url_for('admin_teams'))
                except Exception as e:
                    db.rollback()
                    flash(f"Error adding team: {str(e)}", "danger")

        teams_list = db.execute("""
            SELECT t.*, v.name as venue_name,
                   (SELECT COUNT(*) FROM players WHERE team_id = t.id) as player_count
            FROM teams t
            LEFT JOIN venues v ON t.home_venue_id = v.id
            ORDER BY t.name ASC
        """).fetchall()
        venues_list = db.execute("SELECT id, name FROM venues ORDER BY name ASC").fetchall()

        return render_template('admin/teams.html', teams=teams_list, venues=venues_list)

    @app.route('/admin/teams/edit/<int:team_id>', methods=['POST'])
    @admin_required
    def admin_edit_team(team_id):
        db = get_db()
        name = request.form.get('name', '').strip()
        short_name = request.form.get('short_name', '').strip()
        code = request.form.get('code', '').strip().upper()
        coach = request.form.get('coach', '').strip()
        founded_year = request.form.get('founded_year', type=int)
        home_venue_id = request.form.get('home_venue_id', type=int) or None
        primary_color = request.form.get('primary_color', '#00ff87')
        secondary_color = request.form.get('secondary_color', '#0a192f')
        logo_url = request.form.get('logo_url', '').strip()
        bio = request.form.get('bio', '').strip()

        try:
            db.execute("""
                UPDATE teams
                SET name = ?, short_name = ?, code = ?, coach = ?, founded_year = ?,
                    home_venue_id = ?, primary_color = ?, secondary_color = ?, logo_url = ?, bio = ?
                WHERE id = ?
            """, (name, short_name, code, coach, founded_year, home_venue_id, primary_color, secondary_color, logo_url, bio, team_id))
            db.commit()
            flash(f"Team '{name}' updated successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Failed to update team: {str(e)}", "danger")

        return redirect(url_for('admin_teams'))

    @app.route('/admin/teams/delete/<int:team_id>', methods=['POST'])
    @admin_required
    def admin_delete_team(team_id):
        db = get_db()
        # Check if team is involved in matches
        match_count = db.execute(
            "SELECT COUNT(*) FROM matches WHERE home_team_id = ? OR away_team_id = ?",
            (team_id, team_id)
        ).fetchone()[0]

        if match_count > 0:
            flash(f"Cannot delete team: It is associated with {match_count} match fixture(s). Remove or reassign matches first.", "warning")
            return redirect(url_for('admin_teams'))

        try:
            db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
            db.commit()
            flash("Team deleted successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error deleting team: {str(e)}", "danger")

        return redirect(url_for('admin_teams'))

    # 2. Manage Players
    @app.route('/admin/players', methods=['GET', 'POST'])
    @admin_required
    def admin_players():
        db = get_db()

        if request.method == 'POST':
            team_id = request.form.get('team_id', type=int)
            name = request.form.get('name', '').strip()
            jersey_number = request.form.get('jersey_number', type=int)
            position = request.form.get('position', '').strip()
            nationality = request.form.get('nationality', '').strip()
            photo_url = request.form.get('photo_url', '').strip() or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80'
            goals = request.form.get('goals', 0, type=int)
            assists = request.form.get('assists', 0, type=int)
            matches_played = request.form.get('matches_played', 0, type=int)
            clean_sheets = request.form.get('clean_sheets', 0, type=int)

            if not team_id or not name or not jersey_number or not position:
                flash("Please fill in all mandatory player fields.", "danger")
            else:
                try:
                    db.execute("""
                        INSERT INTO players (team_id, name, jersey_number, position, nationality, photo_url,
                                             goals, assists, matches_played, clean_sheets)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (team_id, name, jersey_number, position, nationality, photo_url, goals, assists, matches_played, clean_sheets))
                    db.commit()
                    flash(f"Player '{name}' (#{jersey_number}) registered successfully!", "success")
                    return redirect(url_for('admin_players'))
                except Exception as e:
                    db.rollback()
                    flash(f"Failed to add player (check for duplicate jersey numbers): {str(e)}", "danger")

        filter_team_id = request.args.get('team_id', type=int)
        sql = """
            SELECT p.*, t.name as team_name, t.short_name as team_short
            FROM players p
            JOIN teams t ON p.team_id = t.id
        """
        params = []
        if filter_team_id:
            sql += " WHERE p.team_id = ?"
            params.append(filter_team_id)
        sql += " ORDER BY t.name ASC, p.jersey_number ASC"

        players_list = db.execute(sql, params).fetchall()
        teams_list = db.execute("SELECT id, name FROM teams ORDER BY name ASC").fetchall()

        return render_template(
            'admin/players.html',
            players=players_list,
            teams=teams_list,
            selected_team=filter_team_id
        )

    @app.route('/admin/players/edit/<int:player_id>', methods=['POST'])
    @admin_required
    def admin_edit_player(player_id):
        db = get_db()
        team_id = request.form.get('team_id', type=int)
        name = request.form.get('name', '').strip()
        jersey_number = request.form.get('jersey_number', type=int)
        position = request.form.get('position', '').strip()
        nationality = request.form.get('nationality', '').strip()
        photo_url = request.form.get('photo_url', '').strip()
        goals = request.form.get('goals', 0, type=int)
        assists = request.form.get('assists', 0, type=int)
        matches_played = request.form.get('matches_played', 0, type=int)
        clean_sheets = request.form.get('clean_sheets', 0, type=int)

        try:
            db.execute("""
                UPDATE players
                SET team_id = ?, name = ?, jersey_number = ?, position = ?, nationality = ?,
                    photo_url = ?, goals = ?, assists = ?, matches_played = ?, clean_sheets = ?
                WHERE id = ?
            """, (team_id, name, jersey_number, position, nationality, photo_url, goals, assists, matches_played, clean_sheets, player_id))
            db.commit()
            flash(f"Player '{name}' updated successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating player: {str(e)}", "danger")

        return redirect(url_for('admin_players'))

    @app.route('/admin/players/delete/<int:player_id>', methods=['POST'])
    @admin_required
    def admin_delete_player(player_id):
        db = get_db()
        try:
            db.execute("DELETE FROM players WHERE id = ?", (player_id,))
            db.commit()
            flash("Player deleted successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error deleting player: {str(e)}", "danger")

        return redirect(url_for('admin_players'))

    # 3. Manage Fixtures
    @app.route('/admin/fixtures', methods=['GET', 'POST'])
    @admin_required
    def admin_fixtures():
        db = get_db()

        if request.method == 'POST':
            season_id = request.form.get('season_id', type=int)
            round_no = request.form.get('round', 1, type=int)
            home_team_id = request.form.get('home_team_id', type=int)
            away_team_id = request.form.get('away_team_id', type=int)
            venue_id = request.form.get('venue_id', type=int) or None
            match_date = request.form.get('match_date', '').strip()
            match_time = request.form.get('match_time', '').strip()
            status = request.form.get('status', 'scheduled')
            summary = request.form.get('summary', '').strip()

            if home_team_id == away_team_id:
                flash("Home team and Away team cannot be the same!", "danger")
            elif not match_date or not match_time:
                flash("Please specify valid match date and kickoff time.", "danger")
            else:
                try:
                    db.execute("""
                        INSERT INTO matches (season_id, round, home_team_id, away_team_id, venue_id, match_date, match_time, status, summary)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (season_id, round_no, home_team_id, away_team_id, venue_id, match_date, match_time, status, summary))
                    db.commit()
                    flash("Fixture successfully scheduled!", "success")
                    return redirect(url_for('admin_fixtures'))
                except Exception as e:
                    db.rollback()
                    flash(f"Error scheduling fixture: {str(e)}", "danger")

        fixtures_list = db.execute("""
            SELECT m.*, ht.name as home_name, at.name as away_name, v.name as venue_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            ORDER BY m.match_date ASC, m.match_time ASC
        """).fetchall()

        teams_list = db.execute("SELECT id, name FROM teams ORDER BY name ASC").fetchall()
        venues_list = db.execute("SELECT id, name FROM venues ORDER BY name ASC").fetchall()
        seasons_list = db.execute("SELECT id, name FROM seasons ORDER BY id DESC").fetchall()

        return render_template(
            'admin/fixtures.html',
            fixtures=fixtures_list,
            teams=teams_list,
            venues=venues_list,
            seasons=seasons_list
        )

    @app.route('/admin/fixtures/edit/<int:match_id>', methods=['POST'])
    @admin_required
    def admin_edit_fixture(match_id):
        db = get_db()
        season_id = request.form.get('season_id', type=int)
        round_no = request.form.get('round', 1, type=int)
        home_team_id = request.form.get('home_team_id', type=int)
        away_team_id = request.form.get('away_team_id', type=int)
        venue_id = request.form.get('venue_id', type=int) or None
        match_date = request.form.get('match_date', '').strip()
        match_time = request.form.get('match_time', '').strip()
        status = request.form.get('status', 'scheduled')
        summary = request.form.get('summary', '').strip()

        if home_team_id == away_team_id:
            flash("Home and Away teams must be distinct.", "danger")
            return redirect(url_for('admin_fixtures'))

        try:
            db.execute("""
                UPDATE matches
                SET season_id = ?, round = ?, home_team_id = ?, away_team_id = ?,
                    venue_id = ?, match_date = ?, match_time = ?, status = ?, summary = ?
                WHERE id = ?
            """, (season_id, round_no, home_team_id, away_team_id, venue_id, match_date, match_time, status, summary, match_id))
            db.commit()
            flash("Fixture updated successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating fixture: {str(e)}", "danger")

        return redirect(url_for('admin_fixtures'))

    @app.route('/admin/fixtures/delete/<int:match_id>', methods=['POST'])
    @admin_required
    def admin_delete_fixture(match_id):
        db = get_db()
        try:
            db.execute("DELETE FROM matches WHERE id = ?", (match_id,))
            db.commit()
            flash("Fixture deleted successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error deleting fixture: {str(e)}", "danger")

        return redirect(url_for('admin_fixtures'))

    # 4. Manage Match Results
    @app.route('/admin/results')
    @admin_required
    def admin_results():
        db = get_db()
        matches_list = db.execute("""
            SELECT m.*, ht.name as home_name, ht.short_name as home_short, ht.logo_url as home_logo,
                   at.name as away_name, at.short_name as away_short, at.logo_url as away_logo,
                   v.name as venue_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            ORDER BY 
                CASE m.status 
                    WHEN 'live' THEN 1 
                    WHEN 'scheduled' THEN 2 
                    WHEN 'completed' THEN 3 
                    ELSE 4 
                END, m.match_date DESC
        """).fetchall()

        return render_template('admin/results.html', matches=matches_list)

    @app.route('/admin/results/update/<int:match_id>', methods=['POST'])
    @admin_required
    def admin_update_result(match_id):
        db = get_db()
        home_score = request.form.get('home_score', 0, type=int)
        away_score = request.form.get('away_score', 0, type=int)
        status = request.form.get('status', 'completed')
        minute = request.form.get('minute', 90 if status == 'completed' else 0, type=int)
        summary = request.form.get('summary', '').strip()

        try:
            db.execute("""
                UPDATE matches
                SET home_score = ?, away_score = ?, status = ?, minute = ?, summary = ?
                WHERE id = ?
            """, (home_score, away_score, status, minute, summary, match_id))
            db.commit()
            flash(f"Match #{match_id} result updated! League standings have been automatically refreshed.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating match result: {str(e)}", "danger")

        return redirect(url_for('admin_results'))

    # 5. Manage Venues
    @app.route('/admin/venues', methods=['GET', 'POST'])
    @admin_required
    def admin_venues():
        db = get_db()

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            city = request.form.get('city', '').strip()
            capacity = request.form.get('capacity', 0, type=int)
            surface = request.form.get('surface', 'Natural Grass').strip()
            image_url = request.form.get('image_url', '').strip() or 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1200&q=80'
            description = request.form.get('description', '').strip()

            if not name or not city or capacity <= 0:
                flash("Please supply a valid stadium name, city, and positive capacity.", "danger")
            else:
                try:
                    db.execute("""
                        INSERT INTO venues (name, city, capacity, surface, image_url, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (name, city, capacity, surface, image_url, description))
                    db.commit()
                    flash(f"Stadium '{name}' added successfully!", "success")
                    return redirect(url_for('admin_venues'))
                except Exception as e:
                    db.rollback()
                    flash(f"Error creating venue: {str(e)}", "danger")

        venues_list = db.execute("""
            SELECT v.*, COUNT(m.id) as match_count
            FROM venues v
            LEFT JOIN matches m ON v.id = m.venue_id
            GROUP BY v.id
            ORDER BY v.name ASC
        """).fetchall()

        return render_template('admin/venues.html', venues=venues_list)

    @app.route('/admin/venues/edit/<int:venue_id>', methods=['POST'])
    @admin_required
    def admin_edit_venue(venue_id):
        db = get_db()
        name = request.form.get('name', '').strip()
        city = request.form.get('city', '').strip()
        capacity = request.form.get('capacity', 0, type=int)
        surface = request.form.get('surface', 'Natural Grass').strip()
        image_url = request.form.get('image_url', '').strip()
        description = request.form.get('description', '').strip()

        try:
            db.execute("""
                UPDATE venues
                SET name = ?, city = ?, capacity = ?, surface = ?, image_url = ?, description = ?
                WHERE id = ?
            """, (name, city, capacity, surface, image_url, description, venue_id))
            db.commit()
            flash(f"Venue '{name}' updated successfully.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error updating venue: {str(e)}", "danger")

        return redirect(url_for('admin_venues'))

    @app.route('/admin/venues/delete/<int:venue_id>', methods=['POST'])
    @admin_required
    def admin_delete_venue(venue_id):
        db = get_db()
        try:
            db.execute("DELETE FROM venues WHERE id = ?", (venue_id,))
            db.commit()
            flash("Venue removed.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error deleting venue: {str(e)}", "danger")

        return redirect(url_for('admin_venues'))

    # 6. Manage Seasons
    @app.route('/admin/seasons', methods=['GET', 'POST'])
    @admin_required
    def admin_seasons():
        db = get_db()
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            year = request.form.get('year', type=int)
            start_date = request.form.get('start_date', '').strip()
            end_date = request.form.get('end_date', '').strip()
            is_active = 1 if request.form.get('is_active') else 0

            if is_active == 1:
                db.execute("UPDATE seasons SET is_active = 0")

            try:
                db.execute("""
                    INSERT INTO seasons (name, year, start_date, end_date, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, year, start_date, end_date, is_active))
                db.commit()
                flash("Season created successfully!", "success")
                return redirect(url_for('admin_seasons'))
            except Exception as e:
                db.rollback()
                flash(f"Error creating season: {str(e)}", "danger")

        seasons_list = db.execute("SELECT * FROM seasons ORDER BY year DESC").fetchall()
        return render_template('admin/seasons.html', seasons=seasons_list)

    @app.route('/admin/seasons/activate/<int:season_id>', methods=['POST'])
    @admin_required
    def admin_activate_season(season_id):
        db = get_db()
        try:
            db.execute("UPDATE seasons SET is_active = 0")
            db.execute("UPDATE seasons SET is_active = 1 WHERE id = ?", (season_id,))
            db.commit()
            flash("Active season updated.", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('admin_seasons'))

    # -------------------------------------------------------------
    # REST API ENDPOINTS
    # -------------------------------------------------------------
    @app.route('/api/standings')
    def api_standings():
        season_id = request.args.get('season_id', type=int)
        standings_data = calculate_standings(season_id)
        return jsonify({'status': 'success', 'data': standings_data})

    @app.route('/api/teams')
    def api_teams():
        db = get_db()
        teams = db.execute("SELECT * FROM teams ORDER BY name ASC").fetchall()
        return jsonify({'status': 'success', 'data': [dict(t) for t in teams]})

    @app.route('/api/players')
    def api_players():
        db = get_db()
        team_id = request.args.get('team_id', type=int)
        if team_id:
            players = db.execute("SELECT * FROM players WHERE team_id = ? ORDER BY jersey_number ASC", (team_id,)).fetchall()
        else:
            players = db.execute("SELECT * FROM players ORDER BY goals DESC").fetchall()
        return jsonify({'status': 'success', 'data': [dict(p) for p in players]})

    @app.route('/api/fixtures')
    def api_fixtures():
        db = get_db()
        matches = db.execute("""
            SELECT m.*, ht.name as home_name, at.name as away_name, v.name as venue_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            ORDER BY m.match_date ASC
        """).fetchall()
        return jsonify({'status': 'success', 'data': [dict(m) for m in matches]})

    @app.route('/api/search')
    def api_search():
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'teams': [], 'players': []})
        db = get_db()
        teams = db.execute("SELECT id, name, short_name, logo_url FROM teams WHERE name LIKE ? OR code LIKE ? LIMIT 5", (f"%{q}%", f"%{q}%")).fetchall()
        players = db.execute("""
            SELECT p.id, p.name, p.position, p.jersey_number, t.short_name as team_name
            FROM players p
            JOIN teams t ON p.team_id = t.id
            WHERE p.name LIKE ? LIMIT 5
        """, (f"%{q}%",)).fetchall()
        return jsonify({
            'teams': [dict(t) for t in teams],
            'players': [dict(p) for p in players]
        })

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ['true', '1']
    app.run(host='0.0.0.0', port=port, debug=debug)
