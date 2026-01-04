import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Fútbol amigos", layout="wide")
st.title("⚽ Puntuaciones fútbol")

# ---------------- AUTH ----------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)

# 🔑 IMPORTANTE: abrir por ID, NO por nombre
SHEET_ID = "1rxldVieuVsM6WBskIo9SjynoSRTS-1vjiyuxX7TkKX0"
sheet = client.open_by_key(SHEET_ID)

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

# ---------------- ADMIN: CARGAR PARTIDO ----------------
with st.expander("🛠️ Cargar partido (Mati)"):
    fecha = st.date_input("Fecha", date.today())
    resultado = st.selectbox(
        "Resultado",
        ["Victoria A", "Empate", "Victoria B"]
    )

    team_a = st.multiselect("Equipo A", players["name"].tolist())
    team_b = st.multiselect("Equipo B", players["name"].tolist())

    if st.button("Guardar partido"):
        if set(team_a) & set(team_b):
            st.error("Un jugador no puede estar en ambos equipos")
        elif len(team_a) == 0 or len(team_b) == 0:
            st.error("Ambos equipos deben tener jugadores")
        else:
            match_id = int(matches["match_id"].max()) + 1 if not matches.empty else 1

            matches_ws.append_row([
                match_id,
                str(fecha),
                resultado
            ])

            for p in team_a:
                pid = int(players.loc[players["name"] == p, "player_id"].values[0])
                mp_ws.append_row([match_id, pid, "A"])

            for p in team_b:
                pid = int(players.loc[players["name"] == p, "player_id"].values[0])
                mp_ws.append_row([match_id, pid, "B"])

            st.success("✅ Partido cargado correctamente")

# ---------------- VOTAR PARTIDO ----------------
st.header("📝 Votar partido")

if matches.empty:
    st.info("Todavía no hay partidos cargados")
    st.stop()

match_id = st.selectbox(
    "Partido",
    matches["match_id"].astype(int).tolist()
)

voter_name = st.selectbox(
    "Quién sos",
    players["name"].tolist()
)

voter_id = int(
    players.loc[players["name"] == voter_name, "player_id"].values[0]
)

ya_voto = False
if not votes_log.empty:
    ya_voto = (
        (votes_log["match_id"] == match_id)
        & (votes_log["voter_id"] == voter_id)
    ).any()

if ya_voto:
    st.warning("⚠️ Ya votaste este partido")
else:
    jugadores = (
        match_players[match_players["match_id"] == match_id]
        .merge(players, on="player_id")
    )

    votos = {}

    for _, row in jugadores.iterrows():
        if int(row["player_id"]) != voter_id:
            votos[int(row["player_id"])] = st.slider(
                row["name"],
                1.0, 10.0, 6.0, 0.5
            )

    if st.button("Enviar votos"):
        for pid, nota in votos.items():
            ratings_ws.append_row([
                match_id,
                pid,
                float(nota)
            ])

        # Log del voto (anonimato)
        votes_ws.append_row([match_id, voter_id])

        st.success("✅ Voto registrado (anónimo)")
