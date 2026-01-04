import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Fútbol Amigos", layout="centered")

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
matches = load_csv("matches", ["match_id", "date", "result"])
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
# Cargar partido
# ------------------------

if section == "Cargar partido":
    st.title("Cargar partido")

    match_date = st.date_input("Fecha", date.today())

    result = st.selectbox(
        "Resultado",
        ["Victoria Equipo A", "Empate", "Victoria Equipo B"]
    )

    st.subheader("Jugadores")

    new_player = st.text_input("Agregar jugador")
    if st.button("Agregar jugador") and new_player:
        if new_player not in players["player"].values:
            players.loc[len(players)] = {"player": new_player}
            save_csv(players, "players")

    selected_players = st.multiselect(
        "Quiénes jugaron",
        players["player"].tolist()
    )

    teams_assignment = {}
    for p in selected_players:
        teams_assignment[p] = st.selectbox(
            f"Equipo de {p}",
            ["A", "B"],
            key=f"{p}_team"
        )

    if st.button("Guardar partido"):
        match_id = matches["match_id"].max() + 1 if not matches.empty else 1

        matches.loc[len(matches)] = {
            "match_id": match_id,
            "date": match_date,
            "result": result
        }
        save_csv(matches, "matches")

        for p in selected_players:
            match_players.loc[len(match_players)] = {
                "match_id": match_id,
                "player": p,
                "team": teams_assignment[p]
            }

        save_csv(match_players, "match_players")
        st.success("Partido cargado")

# ------------------------
# Votar partido
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
        .agg(score=("score", "mean"))
    )

    match_scores["score"] = match_scores["score"].round(1)
    match_scores = match_scores.sort_values("score", ascending=False)

    st.dataframe(match_scores, use_container_width=True)

# ------------------------
# Tabla anual
# ------------------------

if section == "Tabla anual":
    st.title("Tabla anual")

    if ratings.empty:
        st.info("Todavía no hay datos")
        st.stop()

    # Puntaje promedio
    avg_scores = (
        ratings
        .groupby("rated_player", as_index=False)
        .agg(
            avg_score=("score", "mean"),
            matches_played=("match_id", "count")
        )
    )

    # Resultados por jugador
    merged = match_players.merge(matches, on="match_id")

    def outcome(row):
        if row["result"] == "Empate":
            return "draw"
        if row["result"] == "Victoria Equipo A" and row["team"] == "A":
            return "win"
        if row["result"] == "Victoria Equipo B" and row["team"] == "B":
            return "win"
        return "loss"

    merged["outcome"] = merged.apply(outcome, axis=1)

    results = (
        merged
        .groupby(["player", "outcome"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    table = avg_scores.merge(results, left_on="rated_player", right_on="player")

    table["winrate"] = (
        table.get("win", 0) /
        (table.get("win", 0) + table.get("draw", 0) + table.get("loss", 0))
    ).round(2)

    table = table.rename(columns={
        "rated_player": "Jugador",
        "avg_score": "Puntaje promedio",
        "matches_played": "Partidos votados",
        "win": "Victorias",
        "draw": "Empates",
        "loss": "Derrotas",
        "winrate": "Winrate"
    })

    table = table[
        ["Jugador", "Puntaje promedio", "Victorias", "Empates", "Derrotas", "Winrate"]
    ].sort_values("Puntaje promedio", ascending=False)

    table["Puntaje promedio"] = table["Puntaje promedio"].round(1)

    st.dataframe(table, use_container_width=True)


    global_scores["global_score"] = global_scores["global_score"].round(1)
    global_scores = global_scores.sort_values("global_score", ascending=False)

    st.dataframe(global_scores, use_container_width=True)
