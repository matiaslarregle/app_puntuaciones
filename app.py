import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# ---------------- AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
client = gspread.authorize(creds)

SHEET_NAME = "futbol_amigos_db"
sheet = client.open(SHEET_NAME)

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

st.set_page_config(page_title="Fútbol amigos", layout="wide")
st.title("⚽ Puntuaciones fútbol")

# ---------------- ADMIN ----------------
with st.expander("🛠️ Cargar partido (Mati)"):
    fecha = st.date_input("Fecha", date.today())
    resultado = st.selectbox("Resultado", ["A", "B", "Draw"])

    team_a = st.multiselect("Equipo A", players["name"])
    team_b = st.multiselect("Equipo B", players["name"])

    if st.button("Guardar partido"):
        match_id = len(matches) + 1
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

voter = st.selectbox("Quién sos", players["name"])
match_id = st.selectbox("Partido", matches["match_id"])

ya_voto = (
    (votes_log["match_id"] == match_id)
    & (votes_log["voter"] == voter)
).any()

if ya_voto:
    st.warning("Ya votaste este partido")
else:
    jugadores = match_players[
        match_players["match_id"] == match_id
    ].merge(players, on="player_id")

    for _, row in jugadores.iterrows():
        nota = st.slider(
            f"{row['name']}", 1.0, 10.0, 6.0, 0.5
        )
        ratings_ws.append_row([match_id, row["player_id"], nota])

    votes_ws.append_row([match_id, voter])
    st.success("Voto registrado (anónimo)")

# ---------------- TABLA ANUAL ----------------
st.header("📊 Tabla anual")

if not ratings.empty:
    stats = ratings.groupby("rated_player").agg(
        avg_rating=("rating", "mean"),
        matches_played=("match_id", "nunique"),
    ).reset_index()

    stats["avg_rating"] = stats["avg_rating"].round(1)

    stats = stats.merge(
        players, left_on="rated_player", right_on="player_id"
    )

    mp = match_players.merge(matches, on="match_id")

    def results(df):
        g = ((df.team == df.result)).sum()
        e = (df.result == "Draw").sum()
        p = len(df) - g - e
        return pd.Series(
            {"G": g, "E": e, "P": p, "PJ": len(df)}
        )

    res = mp.groupby("player_id").apply(results).reset_index()

    final = stats.merge(res, left_on="rated_player", right_on="player_id")
    final["Winrate"] = (final["G"] / final["PJ"] * 100).round(1)

    st.dataframe(
        final[
            ["name", "avg_rating", "PJ", "G", "E", "P", "Winrate"]
        ].sort_values("avg_rating", ascending=False)
    )


    table["Puntaje promedio"] = table["Puntaje promedio"].round(1)

    st.dataframe(table, use_container_width=True)
