import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Fútbol amigos", layout="wide")
st.title("⚽ Puntuaciones fútbol")

# ---------------- AUTH (SECRETS) ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
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

# ---------------- VOTAR PARTIDO ----------------
st.header("📝 Votar partido")

match_id = st.selectbox("Partido", matches["match_id"].tolist())
voter_name = st.selectbox("Quién sos", players["name"].tolist())
voter_id = players.loc[players["name"] == voter_name, "player_id"].values[0]

ya_voto = (
    (votes_log["match_id"] == match_id)
    & (votes_log["voter_id"] == voter_id)
).any()

if ya_voto:
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

        # LOG DEL VOTO (anonimato garantizado)
        votes_ws.append_row([match_id, voter_id])

        st.success("Voto registrado (anónimo)")

# ---------------- TABLA ANUAL ----------------
st.header("📊 Tabla anual")

if not ratings.empty:
    stats = (
        ratings
        .groupby("rated_player", as_index=False)
        .agg(
            avg_score=("score", "mean"),
            matches_played=("match_id", "nunique"),
        )
    )

    stats["avg_score"] = stats["avg_score"].round(1)
    stats = stats.merge(
        players, left_on="rated_player", right_on="player_id"
    )

    mp = match_players.merge(matches, on="match_id")

    def outcome(row):
        if row["result"] == "Empate":
            return "E"
        if row["result"] == "Victoria A" and row["team"] == "A":
            return "G"
        if row["result"] == "Victoria B" and row["team"] == "B":
            return "G"
        return "P"

    mp["outcome"] = mp.apply(outcome, axis=1)

    res = (
        mp.groupby(["player_id", "outcome"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    final = stats.merge(res, left_on="rated_player", right_on="player_id")
    final["PJ"] = final.get("G", 0) + final.get("E", 0) + final.get("P", 0)
    final["Winrate"] = (final.get("G", 0) / final["PJ"] * 100).round(1)

    st.dataframe(
        final[
            ["name", "avg_score", "PJ", "G", "E", "P", "Winrate"]
        ]
        .rename(columns={
            "name": "Jugador",
            "avg_score": "Puntaje promedio"
        })
        .sort_values("Puntaje promedio", ascending=False),
        use_container_width=True
    )
