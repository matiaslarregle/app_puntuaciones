import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="SofaScore Amigos", layout="centered")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------
# Utils
# ------------------------

def load_csv(name, columns):
    path = f"{DATA_DIR}/{name}.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    df = pd.DataFrame(columns=columns)
    df.to_csv(path, index=False)
    return df


def save_csv(df, name):
    df.to_csv(f"{DATA_DIR}/{name}.csv", index=False)


# ------------------------
# Data
# ------------------------

players = load_csv("players", ["player"])
matches = load_csv("matches", ["match_id", "date", "team_a", "team_b", "winner"])
match_players = load_csv("match_players", ["match_id", "player", "team"])
votes_log = load_csv("votes_log", ["match_id", "player"])
ratings = load_csv("ratings", ["match_id", "rated_player", "score"])

# ------------------------
# Sidebar
# ------------------------

section = st.sidebar.radio(
    "Menú",
    ["Cargar partido", "Votar partido", "Resultado partido", "Tabla anual"]
)

# ------------------------
# Cargar partido (admin)
# ------------------------

if section == "Cargar partido":
    st.title("Cargar partido")

    match_date = st.date_input("Fecha", date.today())
    team_a = st.text_input("Equipo A")
    team_b = st.text_input("Equipo B")

    winner = st.selectbox(
        "Resultado",
        ["Empate", team_a, team_b]
    )

    st.subheader("Jugadores")

    new_player = st.text_input("Agregar jugador")
    if st.button("Agregar") and new_player:
        if new_player not in players["player"].values:
            players.loc[len(players)] = {"player": new_player}
            save_csv(players, "players")

    players_selected = st.multiselect(
        "Quiénes jugaron",
        players["player"].tolist()
    )

    teams_assignment = {}
    for p in players_selected:
        teams_assignment[p] = st.selectbox(
            f"Equipo de {p}",
            [team_a, team_b],
            key=f"{p}_team"
        )

    if st.button("Guardar partido"):
        match_id = matches["match_id"].max() + 1 if not matches.empty else 1

        matches.loc[len(matches)] = {
            "match_id": match_id,
            "date": match_date,
            "team_a": team_a,
            "team_b": team_b,
            "winner": winner
        }
        save_csv(matches, "matches")

        for p in players_selected:
            match_players.loc[len(match_players)] = {
                "match_id": match_id,
                "player": p,
                "team": teams_assignment[p]
            }

        save_csv(match_players, "match_players")

        st.success("Partido cargado")

# ------------------------
# Votar partido (anónimo)
# ------------------------

if section == "Votar partido":
    st.title("Votar partido")

    if matches.empty:
        st.info("No hay partidos cargados")
        st.stop()

    match_id = st.selectbox("Partido", matches["match_id"])
    players_in_match = match_players[
        match_players["match_id"] == match_id
    ]["player"].tolist()

    voter = st.selectbox("¿Quién sos?", players_in_match)

    already_voted = (
        (votes_log["match_id"] == match_id) &
        (votes_log["player"] == voter)
    ).any()

    if already_voted:
        st.warning("Ya votaste este partido")
        st.stop()

    st.subheader("Puntuar compañeros")

    scores = {}
    for p in players_in_match:
        if p != voter:
            scores[p] = st.slider(p, 1, 10, 7)

    if st.button("Enviar votos"):
        votes_log.loc[len(votes_log)] = {
            "match_id": match_id,
            "player": voter
        }
        save_csv(votes_log, "votes_log")

        for rated, score in scores.items():
            ratings.loc[len(ratings)] = {
                "match_id": match_id,
                "rated_player": rated,
                "score": score
            }

        save_csv(ratings, "ratings")

        st.success("Voto registrado")

# ------------------------
# Resultado partido
# ------------------------

if section == "Resultado partido":
    st.title("Resultado del partido")

    if ratings.empty:
        st.info("Todavía no hay votos")
        st.stop()

    match_id = st.selectbox("Partido", matches["match_id"])

    match_scores = (
        ratings[ratings["match_id"] == match_id]
        .groupby("rated_player", as_index=False)
        .agg(match_score=("score", "mean"))
    )

    match_scores["match_score"] = match_scores["match_score"].round(1)
    match_scores = match_scores.sort_values("match_score", ascending=False)

    st.dataframe(match_scores, use_container_width=True)

# ------------------------
# Tabla anual
# ------------------------

if section == "Tabla anual":
    st.title("Tabla anual")

    if ratings.empty:
        st.info("Todavía no hay datos")
        st.stop()

    match_scores = (
        ratings
        .groupby(["match_id", "rated_player"], as_index=False)
        .agg(match_score=("score", "mean"))
    )

    global_scores = (
        match_scores
        .groupby("rated_player", as_index=False)
        .agg(
            global_score=("match_score", "mean"),
            matches_played=("match_id", "count")
        )
    )

    global_scores["global_score"] = global_scores["global_score"].round(1)
    global_scores = global_scores.sort_values("global_score", ascending=False)

    st.dataframe(global_scores, use_container_width=True)
