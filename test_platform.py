import os
import sys

# Ensure root directory is on sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app
from database import get_db, calculate_standings

def run_tests():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    print("====================================================")
    print("      RUNNING SPORTS LEAGUE VERIFICATION TESTS      ")
    print("====================================================")

    # 1. Test Public Routes
    public_routes = [
        '/',
        '/teams',
        '/team/1',
        '/players',
        '/fixtures',
        '/results',
        '/standings',
        '/venues',
        '/statistics',
        '/login'
    ]
    for route in public_routes:
        res = client.get(route)
        assert res.status_code == 200, f"Failed route {route}: Status {res.status_code}"
        print(f" [PASS] Public route: {route} (200 OK)")

    # 2. Test REST API Endpoints
    api_routes = [
        ('/api/standings', 'standings'),
        ('/api/teams', 'teams'),
        ('/api/players', 'players'),
        ('/api/fixtures', 'fixtures'),
        ('/api/search?q=Apex', 'search')
    ]
    for route, name in api_routes:
        res = client.get(route)
        assert res.status_code == 200, f"API {route} failed with {res.status_code}"
        data = res.get_json()
        assert data is not None, f"API {route} returned non-JSON"
        print(f" [PASS] REST API: {route} (JSON Valid)")

    # 3. Test Protected Admin Routes (Unauthenticated)
    admin_routes = [
        '/admin/dashboard',
        '/admin/teams',
        '/admin/players',
        '/admin/fixtures',
        '/admin/results',
        '/admin/venues',
        '/admin/seasons'
    ]
    for route in admin_routes:
        res = client.get(route)
        assert res.status_code in [302, 303], f"Unprotected admin route {route}: {res.status_code}"
        assert '/login' in res.location, f"Route {route} did not redirect to login: {res.location}"
        print(f" [PASS] Protected route: {route} correctly redirects to /login")

    # 4. Test Authentication
    # Invalid login
    res = client.post('/login', data={'username': 'admin', 'password': 'WrongPassword123'}, follow_redirects=True)
    assert b"Invalid credentials" in res.data, "Failed to reject invalid login"
    print(" [PASS] Invalid admin login correctly rejected")

    # Valid login
    res = client.post('/login', data={'username': 'admin@sportsleague.com', 'password': 'Admin@2026!'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Chief Tournament Administrator" in res.data or b"Dashboard" in res.data, "Failed to authenticate valid admin"
    print(" [PASS] Valid admin login succeeded with secure session")

    # 5. Test Admin CRUD
    # A. Add Team
    res = client.post('/admin/teams', data={
        'name': 'Test Galaxy FC',
        'short_name': 'Galaxy',
        'code': 'TGX',
        'coach': 'Carl Sagan',
        'founded_year': 2020,
        'home_venue_id': 1,
        'primary_color': '#00ff87',
        'secondary_color': '#050a14',
        'logo_url': 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=300&q=80',
        'bio': 'Test club created during automated test.'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Test Galaxy FC" in res.data
    print(" [PASS] Admin: Created new club 'Test Galaxy FC'")

    with app.app_context():
        db = get_db()
        team_id = db.execute("SELECT id FROM teams WHERE code = 'TGX'").fetchone()['id']

    # B. Edit Team
    res = client.post(f'/admin/teams/edit/{team_id}', data={
        'name': 'Test Galaxy United',
        'short_name': 'Galaxy Utd',
        'code': 'TGU',
        'coach': 'Carl Sagan Jr.',
        'founded_year': 2021,
        'home_venue_id': 1,
        'primary_color': '#00e5ff',
        'secondary_color': '#050a14',
        'logo_url': 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=300&q=80',
        'bio': 'Updated bio.'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Test Galaxy United" in res.data
    print(" [PASS] Admin: Edited club details successfully")

    # C. Add Player
    res = client.post('/admin/players', data={
        'team_id': team_id,
        'name': 'Lucas Test Striker',
        'jersey_number': 99,
        'position': 'Forward',
        'nationality': 'Brazil',
        'photo_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80',
        'goals': 5,
        'assists': 2,
        'matches_played': 3,
        'clean_sheets': 0
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Lucas Test Striker" in res.data
    print(" [PASS] Admin: Added player 'Lucas Test Striker' (#99)")

    with app.app_context():
        db = get_db()
        player_id = db.execute("SELECT id FROM players WHERE name = 'Lucas Test Striker'").fetchone()['id']

    # D. Schedule Fixture
    with app.app_context():
        db = get_db()
        other_team_id = db.execute("SELECT id FROM teams WHERE code = 'ATH'").fetchone()['id']
        season_id = db.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()['id']

    res = client.post('/admin/fixtures', data={
        'season_id': season_id,
        'round': 5,
        'home_team_id': team_id,
        'away_team_id': other_team_id,
        'venue_id': 1,
        'match_date': '2026-12-01',
        'match_time': '20:00',
        'status': 'scheduled',
        'summary': 'Test automated match.'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Fixture successfully scheduled" in res.data
    print(" [PASS] Admin: Scheduled new match fixture")

    with app.app_context():
        db = get_db()
        match_id = db.execute("SELECT id FROM matches WHERE round = 5 AND home_team_id = ?", (team_id,)).fetchone()['id']

    # E. Record Match Result & Verify Dynamic Standings Update
    res = client.post(f'/admin/results/update/{match_id}', data={
        'home_score': 4,
        'away_score': 1,
        'status': 'completed',
        'minute': 90,
        'summary': 'Galaxy United scored 4 goals in a dominant performance.'
    }, follow_redirects=True)
    assert res.status_code == 200
    print(" [PASS] Admin: Certified final match score 4 - 1")

    with app.app_context():
        standings = calculate_standings(season_id)
        galaxy_standing = next((s for s in standings if s['team_id'] == team_id), None)
        assert galaxy_standing is not None, "Galaxy United not found in standings"
        assert galaxy_standing['played'] == 1, f"Expected 1 played, got {galaxy_standing['played']}"
        assert galaxy_standing['won'] == 1, f"Expected 1 win, got {galaxy_standing['won']}"
        assert galaxy_standing['points'] == 3, f"Expected 3 points, got {galaxy_standing['points']}"
        assert galaxy_standing['goals_for'] == 4, f"Expected 4 GF, got {galaxy_standing['goals_for']}"
        assert galaxy_standing['goal_difference'] == 3, f"Expected +3 GD, got {galaxy_standing['goal_difference']}"
        assert len(galaxy_standing['form_last5']) >= 1 and galaxy_standing['form_last5'][-1]['result'] == 'W', "Form guide did not record win"
        print(" [PASS] Verification: Points table, Goal Difference, and Form accurately recalculated!")

    # F. Clean up test match, player, and team
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        db.execute("DELETE FROM players WHERE id = ?", (player_id,))
        db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        db.commit()
    print(" [PASS] Admin: Cleaned up test entities safely")

    # 6. Test Logout
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b"logged out" in res.data
    print(" [PASS] Admin: Logout successfully terminated session")

    print("====================================================")
    print("      ALL 12/12 INTEGRATION TESTS PASSED 100%!      ")
    print("====================================================")

if __name__ == '__main__':
    run_tests()
