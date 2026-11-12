import os
import sys
from werkzeug.security import generate_password_hash

# Ensure root directory is on sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)

from config import Config
from database import get_db, init_db
from flask import Flask

def seed_database():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['BASE_DIR'] = BASE_DIR

    with app.app_context():
        # Initialize schema
        init_db(app)
        db = get_db()

        # Check if already seeded
        admin_count = db.execute("SELECT COUNT(*) as count FROM admins").fetchone()['count']
        if admin_count > 0:
            print("Database already contains data. Cleaning and re-seeding for clean demo...")
            db.execute("DELETE FROM matches")
            db.execute("DELETE FROM players")
            db.execute("DELETE FROM teams")
            db.execute("DELETE FROM venues")
            db.execute("DELETE FROM seasons")
            db.execute("DELETE FROM admins")
            db.commit()

        print("Seeding Administrator...")
        db.execute("""
            INSERT INTO admins (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'admin',
            'admin@sportsleague.com',
            generate_password_hash('Admin@2026!'),
            'Chief Tournament Administrator',
            'superadmin'
        ))

        print("Seeding Seasons...")
        db.execute("""
            INSERT INTO seasons (name, year, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'Apex Championship 2026',
            2026,
            '2026-08-15',
            '2027-05-30',
            1
        ))
        season_id = db.execute("SELECT id FROM seasons WHERE is_active = 1").fetchone()['id']

        print("Seeding Venues...")
        venues_data = [
            ('Apex National Stadium', 'Metropolis City', 68500, 'Natural Grass', 
             'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1200&q=80',
             'The premier sports venue with cutting-edge LED floodlights, hybrid turf, and panoramic glass roof.'),
            ('Neon Thunder Arena', 'Cyberport Bay', 52000, 'Reinforced Hybrid', 
             'https://images.unsplash.com/photo-1522778119026-d647f0596c20?auto=format&fit=crop&w=1200&q=80',
             'State-of-the-art waterfront arena known for deafening acoustic resonance and vibrant night illuminations.'),
            ('Solaris Olympic Park', 'Solaria Central', 60000, 'Natural Grass', 
             'https://images.unsplash.com/photo-1577223625816-7546f13df25d?auto=format&fit=crop&w=1200&q=80',
             'Eco-powered architectural marvel featuring zero-emission stadium power and world-class pitch heating.'),
            ('Iron Fortress Grounds', 'Steel Valley', 45200, 'Natural Grass', 
             'https://images.unsplash.com/photo-1518091043644-c1d4457512c6?auto=format&fit=crop&w=1200&q=80',
             'Historic cauldron of grit and football tradition, flanked by towering steel pylons and fervent fan terraces.')
        ]

        venue_ids = []
        for name, city, cap, surface, img, desc in venues_data:
            cursor = db.execute("""
                INSERT INTO venues (name, city, capacity, surface, image_url, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, city, cap, surface, img, desc))
            venue_ids.append(cursor.lastrowid)

        print("Seeding Teams...")
        teams_data = [
            ('Apex Thunder FC', 'Apex Thunder', 'ATH', 'Marcus Sterling', 1994, venue_ids[0], '#00ff87', '#061325',
             'https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=300&q=80',
             'High-tempo attacking powerhouse characterized by electrifying wing play and relentless pressing.'),
            ('Neon Strikers', 'Neon Strikers', 'NST', 'Elena Vance', 2008, venue_ids[1], '#00e5ff', '#0a192f',
             'https://images.unsplash.com/photo-1511886929837-354d827aae26?auto=format&fit=crop&w=300&q=80',
             'Dynamic coastal football club renowned for clinical counter-attacks and creative playmaking.'),
            ('Cyber City FC', 'Cyber City', 'CCF', 'Julian Romero', 2012, venue_ids[1], '#9d4edd', '#100b20',
             'https://images.unsplash.com/photo-1560272564-c83b66b1ad12?auto=format&fit=crop&w=300&q=80',
             'Tactical innovators blending data-driven positional mastery with fluid tiki-taka combinations.'),
            ('Vanguard United', 'Vanguard Utd', 'VUN', 'David Thorne', 1988, venue_ids[3], '#ff0055', '#1a0610',
             'https://images.unsplash.com/photo-1529900248671-561b3699c680?auto=format&fit=crop&w=300&q=80',
             'Steely and disciplined warriors with an impregnable defensive block and lethal set-piece delivery.'),
            ('Solar Dynamo', 'Solar Dynamo', 'SDY', 'Lucas Moretti', 2001, venue_ids[2], '#ffbe0b', '#1f1604',
             'https://images.unsplash.com/photo-1551958219-acbc608c6377?auto=format&fit=crop&w=300&q=80',
             'Fluid, high-scoring side with South American flair, quick one-twos, and dazzling free-kicks.'),
            ('Ironclad FC', 'Ironclad FC', 'IFC', 'Viktor Petrov', 1976, venue_ids[3], '#38bdf8', '#0c1a29',
             'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=300&q=80',
             'Traditional heavyweights built on physical fortitude, uncompromising aerial dominance, and pride.'),
            ('Metro Knights', 'Metro Knights', 'MKN', 'Antoine Dubois', 1999, venue_ids[0], '#3b82f6', '#09152b',
             'https://images.unsplash.com/photo-1517466787929-bc90951d0974?auto=format&fit=crop&w=300&q=80',
             'Capital city favorites who command midfield battles with elegance and pinpoint deep passing.'),
            ('Phoenix Athletic', 'Phoenix Ath', 'PHA', 'Javier Ortega', 2015, venue_ids[2], '#f97316', '#1c0e05',
             'https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?auto=format&fit=crop&w=300&q=80',
             'Explosive rising contenders famous for dramatic second-half comebacks and fierce fighting spirit.')
        ]

        team_ids = []
        for name, sname, code, coach, founded, vid, pcol, scol, logo, bio in teams_data:
            cursor = db.execute("""
                INSERT INTO teams (name, short_name, code, coach, founded_year, home_venue_id, primary_color, secondary_color, logo_url, bio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, sname, code, coach, founded, vid, pcol, scol, logo, bio))
            team_ids.append(cursor.lastrowid)

        print("Seeding Players (5 per team = 40 players)...")
        # Template of 5 positions per team: GK, DEF, MID, MID, FWD
        players_roster = [
            # Team 0: Apex Thunder FC
            [
                ('Hugo Lindqvist', 1, 'Goalkeeper', 'Sweden', 6, 0, 0, 0, 0, 3),
                ('Darius Vance', 4, 'Defender', 'England', 6, 1, 1, 1, 0, 3),
                ('Mateo Silva', 8, 'Midfielder', 'Spain', 6, 2, 4, 1, 0, 0),
                ('Kai Takahashi', 10, 'Midfielder', 'Japan', 6, 3, 3, 0, 0, 0),
                ('Alexandre Mercier', 9, 'Forward', 'France', 6, 7, 2, 0, 0, 0),
            ],
            # Team 1: Neon Strikers
            [
                ('Roman Keller', 1, 'Goalkeeper', 'Germany', 6, 0, 0, 0, 0, 2),
                ('Gabriel Santos', 3, 'Defender', 'Brazil', 6, 1, 0, 2, 0, 2),
                ('Luka Modric-Smith', 7, 'Midfielder', 'Croatia', 6, 2, 5, 1, 0, 0),
                ('Tariq Al-Mansoor', 11, 'Midfielder', 'Morocco', 6, 4, 2, 0, 0, 0),
                ('Dominic Cruz', 9, 'Forward', 'Argentina', 6, 5, 1, 1, 0, 0),
            ],
            # Team 2: Cyber City FC
            [
                ('Liam O\'Connor', 13, 'Goalkeeper', 'Ireland', 5, 0, 0, 0, 0, 1),
                ('Samuel Kim', 5, 'Defender', 'South Korea', 5, 0, 1, 1, 0, 1),
                ('Florian Brandt', 6, 'Midfielder', 'Germany', 5, 2, 3, 2, 0, 0),
                ('Enzo Rossi', 10, 'Midfielder', 'Italy', 5, 3, 2, 0, 0, 0),
                ('Malik Dembele', 11, 'Forward', 'France', 5, 4, 2, 1, 0, 0),
            ],
            # Team 3: Vanguard United
            [
                ('Arthur Pendelton', 1, 'Goalkeeper', 'England', 5, 0, 0, 0, 0, 3),
                ('Bram van Dijk', 4, 'Defender', 'Netherlands', 5, 2, 0, 1, 0, 3),
                ('Declan Byrne', 8, 'Midfielder', 'Scotland', 5, 1, 2, 2, 0, 0),
                ('Tiago Mendes', 17, 'Midfielder', 'Portugal', 5, 1, 1, 0, 0, 0),
                ('Callum McGregor', 9, 'Forward', 'England', 5, 3, 1, 1, 0, 0),
            ],
            # Team 4: Solar Dynamo
            [
                ('Emiliano Fernandez', 12, 'Goalkeeper', 'Argentina', 6, 0, 0, 1, 0, 1),
                ('Carlos Santana', 2, 'Defender', 'Mexico', 6, 1, 2, 1, 0, 1),
                ('Thiago Alcantara Jr', 10, 'Midfielder', 'Brazil', 6, 3, 4, 0, 0, 0),
                ('Leo Gomez', 8, 'Midfielder', 'Uruguay', 6, 2, 2, 1, 0, 0),
                ('Santiago Alvarez', 19, 'Forward', 'Colombia', 6, 5, 3, 0, 0, 0),
            ],
            # Team 5: Ironclad FC
            [
                ('Milan Horvat', 1, 'Goalkeeper', 'Croatia', 5, 0, 0, 0, 0, 2),
                ('Nikolai Voronin', 5, 'Defender', 'Czechia', 5, 1, 0, 3, 1, 2),
                ('Lars Lindemann', 6, 'Midfielder', 'Denmark', 5, 1, 1, 2, 0, 0),
                ('Marko Jankovic', 14, 'Midfielder', 'Serbia', 5, 1, 1, 1, 0, 0),
                ('Goran Dragic', 9, 'Forward', 'Slovenia', 5, 3, 0, 1, 0, 0),
            ],
            # Team 6: Metro Knights
            [
                ('Etienne Laurent', 1, 'Goalkeeper', 'France', 5, 0, 0, 0, 0, 1),
                ('Cedric Dupont', 3, 'Defender', 'Belgium', 5, 0, 1, 0, 0, 1),
                ('Oliver Wright', 8, 'Midfielder', 'England', 5, 2, 2, 1, 0, 0),
                ('Julian Draxler-Cole', 10, 'Midfielder', 'Germany', 5, 2, 3, 0, 0, 0),
                ('Maxime Renard', 7, 'Forward', 'France', 5, 3, 1, 1, 0, 0),
            ],
            # Team 7: Phoenix Athletic
            [
                ('Diego Morales', 13, 'Goalkeeper', 'Spain', 6, 0, 0, 1, 0, 1),
                ('Inaki Aguirre', 4, 'Defender', 'Spain', 6, 1, 0, 2, 0, 1),
                ('Pablo Ruiz', 8, 'Midfielder', 'Chile', 6, 2, 3, 1, 0, 0),
                ('Felipe Calderon', 11, 'Midfielder', 'Peru', 6, 3, 2, 0, 0, 0),
                ('Angel Navarro', 9, 'Forward', 'Spain', 6, 6, 2, 1, 0, 0),
            ]
        ]

        player_photos = [
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80',
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80',
            'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80',
            'https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80',
            'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=300&q=80',
        ]

        for t_idx, roster in enumerate(players_roster):
            curr_tid = team_ids[t_idx]
            for p_idx, p in enumerate(roster):
                p_name, j_num, pos, nat, mp, g, a, yc, rc, cs = p
                photo = player_photos[p_idx % len(player_photos)]
                db.execute("""
                    INSERT INTO players (team_id, name, jersey_number, position, nationality, photo_url,
                                        matches_played, goals, assists, yellow_cards, red_cards, clean_sheets)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (curr_tid, p_name, j_num, pos, nat, photo, mp, g, a, yc, rc, cs))

        print("Seeding Matches (Completed, Live, and Scheduled Fixtures)...")
        # 8 Completed matches
        completed_matches = [
            (season_id, 1, team_ids[0], team_ids[6], venue_ids[0], '2026-09-02', '18:30', 'completed', 3, 1, 90,
             'Apex Thunder opened their campaign in blistering form with a brace from Alexandre Mercier.'),
            (season_id, 1, team_ids[1], team_ids[4], venue_ids[1], '2026-09-02', '20:45', 'completed', 2, 2, 90,
             'A pulsating four-goal thriller at Neon Thunder Arena ending with a 93rd-minute equalizer.'),
            (season_id, 1, team_ids[3], team_ids[5], venue_ids[3], '2026-09-03', '15:00', 'completed', 1, 0, 90,
             'Vanguard United ground out a vintage 1-0 clean sheet win courtesy of a towering Bram van Dijk header.'),
            (season_id, 1, team_ids[2], team_ids[7], venue_ids[1], '2026-09-03', '17:30', 'completed', 2, 3, 90,
             'Phoenix Athletic staged a sensational away comeback, scoring twice in the final ten minutes.'),
            (season_id, 2, team_ids[0], team_ids[4], venue_ids[0], '2026-09-10', '19:00', 'completed', 2, 0, 90,
             'Clinical finishing and a commanding clean sheet vaulted Apex Thunder to the top of the table.'),
            (season_id, 2, team_ids[6], team_ids[1], venue_ids[0], '2026-09-10', '21:00', 'completed', 1, 2, 90,
             'Dominic Cruz struck in the 88th minute to snatch all three points on the road for the Strikers.'),
            (season_id, 2, team_ids[7], team_ids[3], venue_ids[2], '2026-09-11', '16:00', 'completed', 2, 1, 90,
             'Angel Navarro continued his red-hot scoring streak with a laser strike into the top corner.'),
            (season_id, 2, team_ids[5], team_ids[2], venue_ids[3], '2026-09-11', '18:15', 'completed', 1, 1, 90,
             'A physical midfield war ending all square at Iron Fortress Grounds.')
        ]

        for m in completed_matches:
            db.execute("""
                INSERT INTO matches (season_id, round, home_team_id, away_team_id, venue_id, match_date, match_time, status, home_score, away_score, minute, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, m)

        # 1 Live match with active pulse
        db.execute("""
            INSERT INTO matches (season_id, round, home_team_id, away_team_id, venue_id, match_date, match_time, status, home_score, away_score, minute, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (season_id, 3, team_ids[3], team_ids[2], venue_ids[3], '2026-11-12', '19:45', 'live', 1, 1, 68,
              'High-stakes tactical duel under the floodlights. Both sides pushing fiercely for the breakthrough.'))

        # 6 Upcoming Scheduled matches
        scheduled_matches = [
            (season_id, 3, team_ids[0], team_ids[1], venue_ids[0], '2026-11-15', '20:00', 'scheduled', 0, 0, 0,
             'Super Sunday Derby: 1st place Apex Thunder FC host 2nd place Neon Strikers in an epic showdown.'),
            (season_id, 3, team_ids[4], team_ids[7], venue_ids[2], '2026-11-16', '17:30', 'scheduled', 0, 0, 0,
             'Attack vs Attack: Two of the most prolific offensive units clash at Solaris Olympic Park.'),
            (season_id, 3, team_ids[6], team_ids[5], venue_ids[0], '2026-11-16', '20:15', 'scheduled', 0, 0, 0,
             'Metro Knights look to rebound at home against the formidable defensive wall of Ironclad FC.'),
            (season_id, 4, team_ids[1], team_ids[3], venue_ids[1], '2026-11-22', '18:45', 'scheduled', 0, 0, 0,
             'Round 4 opening fixture: Neon Strikers face Vanguard United at Cyberport Bay.'),
            (season_id, 4, team_ids[2], team_ids[0], venue_ids[1], '2026-11-23', '20:00', 'scheduled', 0, 0, 0,
             'Cyber City take on Apex Thunder in a battle of technical speed vs counter-pressing.'),
            (season_id, 4, team_ids[7], team_ids[6], venue_ids[2], '2026-11-24', '16:00', 'scheduled', 0, 0, 0,
             'Phoenix Athletic host Metro Knights in a crucial mid-season clash.')
        ]

        for sm in scheduled_matches:
            db.execute("""
                INSERT INTO matches (season_id, round, home_team_id, away_team_id, venue_id, match_date, match_time, status, home_score, away_score, minute, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sm)

        db.commit()
        print("Database successfully seeded with realistic tournament data!")
        print("Default Admin: admin@sportsleague.com / Admin@2026!")

if __name__ == '__main__':
    seed_database()
