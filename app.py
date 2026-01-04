import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Fútbol amigos", layout="wide")
st.title("⚽ Puntuaciones fútbol")

# ---------------- AUTH ----------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope,
)

client = gspread.authorize(creds)

SHEET_NAME = "futbol_amigos_db"
sheet = client.open(SHEET_NAME)

# ---------------- LOAD SHEETS ----------------
players_ws = sheet.worksheet("players")
matches_ws = sheet.worksheet("matches")
mp_ws = sheet.worksheet("match_players")
ratings_ws = sheet.worksheet("ratings")
votes_ws = sheet.worksheet("votes_log")

players = pd.DataFrame(players_ws.get_all_records())
matches = pd.DataFrame(matches_ws.get_all_records())
match_players = pd.DataFrame(mp_ws.get_all_records())
ratings = pd.DataFrame(ratings_ws.get_all_records())
votes_log = pd.DataFrame(votes_ws.get_all_records())

# ---------------- ADMIN ----------------
with st.expander("🛠️ Cargar partido (Mati)"):
    fecha = st.date_input("Fecha", date.today())
    resultado = st.selectbox("Resultado", ["Victoria A", "Empate", "Victoria B"])

    team_a = st.multiselect("Equipo A", players["name"])
    team_b = st.multiselect("Equipo B", players["name"])

    if st.button("Guardar partido"):
        if set(team_a) & set(team_b):
            st.error("Un jugador no puede estar en ambos equipos")
        else:
            match_id = matches["match_id"].max() + 1 if not matches.empty else 1
            matches_ws.append_row([match_id, str(fecha), resultado])

            for p in team_a:
                pid = players.loc[players["name"] == p, "player_id"].values[0]
                mp_ws.append_row([match_id, pid, "A"])

            for p in team_b:
                pid = players.loc[players["name"] == p, "player_id"].values[0]
                mp_ws.append_row([match_id, pid, "B"])

            st.success("Partido cargado")

# ---------------- VOTAR ----------------
st.header("📝 Votar partido")

match_id = st.selectbox("Partido", matches["match_id"])
voter_name = st.selectbox("Quién sos", players["name"])
voter_id = players.loc[players["name"] == voter_name, "player_id"].values[0]

if not votes_log.empty and (
    (votes_log["match_id"] == match_id) &
    (votes_log["voter_id"] == voter_id)
).any():
    st.warning("Ya votaste este partido")
else:
    jugadores = (
        match_players[match_players["match_id"] == match_id]
        .merge(players, on="player_id")
    )

    votos = {}
    for _, row in jugadores.iterrows():
        if row["player_id"] != voter_id:
            votos[row["player_id"]] = st.slider(
                row["name"], 1.0, 10.0, 6.0, 0.5
            )

    if st.button("Enviar votos"):
        for pid, nota in votos.items():
            ratings_ws.append_row([match_id, pid, nota])

        votes_ws.append_row([match_id, voter_id])
        st.success("Voto registrado (anónimo)")
