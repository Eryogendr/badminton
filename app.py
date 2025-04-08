# streamlit_app.py
import streamlit as st
import uuid
import os
import json
from datetime import datetime
import random
DATA_DIR = "tournament_data"
os.makedirs(DATA_DIR, exist_ok=True)

st.set_page_config(page_title="🏸 Badminton Tournament", layout="wide")

# Helper functions
def load_tournament(code):
    path = os.path.join(DATA_DIR, f"{code}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def save_tournament(code, data):
    path = os.path.join(DATA_DIR, f"{code}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def generate_code():
    return uuid.uuid4().hex[:6].upper()

# Session state
if "tournament_code" not in st.session_state:
    st.session_state.tournament_code = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Sidebar: Join or create a tournament
with st.sidebar:
    st.title("🎮 Join or Create Tournament")

    mode = st.radio("Mode", ["Join", "Create"])

    if mode == "Create":
        admin_name = st.text_input("Your Name (Admin)")
        if st.button("Create Tournament") and admin_name:
            code = generate_code()
            data = {
                "admin": admin_name,
                "players": [],
                "teams": [],
                "matches": [],
                "results": [],
                "created": str(datetime.now()),
                "locked": False,
                "court_assignments": [],
                "played_matches": []
            }
            save_tournament(code, data)
            st.session_state.tournament_code = code
            st.session_state.is_admin = True
            st.success(f"Tournament created with code: {code}")

    else:  # Join
        code = st.text_input("Enter Tournament Code")
        your_name = st.text_input("Your Name")
        if st.button("Join Tournament") and code and your_name:
            data = load_tournament(code.upper())
            if data:
                st.session_state.tournament_code = code.upper()
                st.session_state.is_admin = (your_name == data["admin"])
                st.success(f"Joined tournament {code.upper()}")
            else:
                st.error("Tournament not found")

# Main
code = st.session_state.tournament_code
if code:
    tournament = load_tournament(code)
    st.header(f"🏸 Tournament Code: {code}")
    st.subheader(f"Created by: {tournament['admin']}")

    if not tournament["locked"]:
        st.subheader("👥 Register Player")
        name = st.text_input("Player Name")
        photo = st.file_uploader("Upload Photo", type=["jpg", "png"])

        if st.button("Register") and name:
            if any(p["name"] == name for p in tournament["players"]):
                st.warning("Name already registered")
            else:
                new_player = {"name": name, "photo": photo.name if photo else ""}
                tournament["players"].append(new_player)
                save_tournament(code, tournament)
                st.success(f"{name} registered")

    st.subheader("📋 Registered Players")
    for p in tournament["players"]:
        st.markdown(f"- {p['name']}")

    if st.session_state.is_admin:
        st.subheader("🔐 Admin Controls")
        if st.button("Lock Registration & Generate Teams"):
            import random
            players = tournament["players"]
            if len(players) < 4:
                st.error("At least 4 players required")
            else:
                random.shuffle(players)
                teams = [players[i:i + 2] for i in range(0, len(players), 2)]
                tournament["teams"] = teams
                tournament["locked"] = True
                save_tournament(code, tournament)
                st.success("Teams created and registration locked")

    if tournament["locked"]:
        st.subheader("🎯 Teams")
        for idx, team in enumerate(tournament["teams"], 1):
            names = ", ".join(p["name"] for p in team)
            st.markdown(f"**Team {idx}:** {names}")

        st.subheader("🏓 Live Court Matches (2 Courts)")
        import itertools
        import random

        # Generate remaining matches
        total_teams = len(tournament["teams"])
        all_possible = list(itertools.combinations(range(total_teams), 2))
        played = [tuple(sorted([t1, t2])) for t1, t2 in tournament["played_matches"]]
        remaining = [m for m in all_possible if tuple(sorted(m)) not in played]

        # Assign 2 matches if not already ongoing
        ongoing = tournament.get("court_assignments", [])
        max_courts = 2

        if len(ongoing) < max_courts and st.session_state.is_admin:
            for _ in range(max_courts - len(ongoing)):
                if remaining:
                    next_match = remaining.pop(0)
                    ongoing.append({"match": next_match, "status": "ongoing"})
        tournament["court_assignments"] = ongoing
        save_tournament(code, tournament)

        # Show ongoing matches and allow result entry
        for court_id, assignment in enumerate(tournament["court_assignments"]):
            t1_idx, t2_idx = assignment["match"]
            team1 = tournament["teams"][t1_idx]
            team2 = tournament["teams"][t2_idx]
            t1_names = ", ".join(p["name"] for p in team1)
            t2_names = ", ".join(p["name"] for p in team2)
            st.markdown(f"### 🏟️ Court {court_id+1}: Team {t1_idx+1} vs Team {t2_idx+1}")
            st.markdown(f"- Team {t1_idx+1}: {t1_names}")
            st.markdown(f"- Team {t2_idx+1}: {t2_names}")

            if st.session_state.is_admin and assignment["status"] == "ongoing":
                winner = st.radio(f"Select Winner (Court {court_id+1})", [t1_idx, t2_idx], format_func=lambda x: f"Team {x+1}", key=f"winner_court_{court_id}")
                if st.button(f"Submit Result (Court {court_id+1})"):
                    tournament["results"].append({"match": assignment["match"], "winner": winner})
                    tournament["played_matches"].append(list(assignment["match"]))
                    tournament["court_assignments"][court_id]["status"] = "completed"
                    save_tournament(code, tournament)
                    st.experimental_rerun()

        # Leaderboard
        st.subheader("🏆 Leaderboard")
        team_wins = {i: 0 for i in range(len(tournament["teams"]))}
        for r in tournament["results"]:
            team_wins[r["winner"]] += 1
        sorted_teams = sorted(team_wins.items(), key=lambda x: x[1], reverse=True)
        for rank, (idx, wins) in enumerate(sorted_teams, 1):
            team_names = ", ".join(p["name"] for p in tournament["teams"][idx])
            st.markdown(f"**{rank}. Team {idx+1}** ({wins} wins) – {team_names}")

else:
    st.info("Please create or join a tournament from the sidebar.")
