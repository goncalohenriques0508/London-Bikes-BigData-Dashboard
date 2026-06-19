import os
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pymongo import MongoClient
from pymongo.errors import PyMongoError


st.set_page_config(
    page_title="London Bikes Dashboard",
    page_icon=":bike:",
    layout="wide",
)


DB_NAME = "london_bikes"
MODELLED_COLLECTION = "bikes_modelled_summer"

LEVEL_ORDER = ["Frequente", "Moderado", "Excessivo"]
LEVEL_COLORS = {
    "Frequente": "#f59e0b",
    "Moderado": "#2f9e44",
    "Excessivo": "#d9480f",
}
LEVEL_MARKER_COLORS = {
    "Frequente": "orange",
    "Moderado": "green",
    "Excessivo": "red",
}
LEVEL_DESCRIPTIONS = {
    "Frequente": "Uso regular e equilibrado da estacao.",
    "Moderado": "Maior disponibilidade de bicicletas no momento observado.",
    "Excessivo": "Muitas docas vazias, sugerindo pressao de utilizacao.",
}
MONGO_URIS = [
    os.getenv("MONGO_URI", "").strip(),
    "mongodb://localhost:27018/",
    "mongodb://mongodb:27017/",
]


def _normalize_uri_candidates() -> list[str]:
    seen = set()
    uris = []
    for uri in MONGO_URIS:
        if uri and uri not in seen:
            seen.add(uri)
            uris.append(uri)
    return uris


@st.cache_resource(show_spinner=False)
def get_database():
    errors = []
    for uri in _normalize_uri_candidates():
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            return client[DB_NAME], uri
        except PyMongoError as exc:
            errors.append(f"{uri} -> {exc}")
    raise RuntimeError(
        "Nao foi possivel ligar ao MongoDB. Tentativas: " + " | ".join(errors)
    )


@st.cache_data(show_spinner=False)
def get_available_dates() -> list:
    db, _ = get_database()
    values = db[MODELLED_COLLECTION].distinct("Date")
    return sorted(value.date() for value in values if isinstance(value, datetime))


@st.cache_data(show_spinner=False)
def get_available_hours(selected_date) -> list[int]:
    db, _ = get_database()
    docs = db[MODELLED_COLLECTION].find(
        {"Date": datetime.combine(selected_date, datetime.min.time())},
        {"Hour": 1, "_id": 0},
    )
    return sorted({doc["Hour"] for doc in docs if "Hour" in doc})


@st.cache_data(show_spinner=False)
def get_available_minutes(selected_date, selected_hour) -> list[int]:
    db, _ = get_database()
    docs = db[MODELLED_COLLECTION].find(
        {
            "Date": datetime.combine(selected_date, datetime.min.time()),
            "Hour": int(selected_hour),
        },
        {"Minute": 1, "_id": 0},
    )
    return sorted({doc["Minute"] for doc in docs if "Minute" in doc})


@st.cache_data(show_spinner=False)
def load_snapshot(selected_date, selected_hour, selected_minute) -> pd.DataFrame:
    db, _ = get_database()
    docs = list(
        db[MODELLED_COLLECTION].find(
            {
                "Date": datetime.combine(selected_date, datetime.min.time()),
                "Hour": int(selected_hour),
                "Minute": int(selected_minute),
            },
            {
                "_id": 0,
                "query_time": 1,
                "Date": 1,
                "Hour": 1,
                "Minute": 1,
                "place_id": 1,
                "common_name": 1,
                "lat": 1,
                "lon": 1,
                "bikes": 1,
                "empty_docks": 1,
                "docks": 1,
                "cluster_id": 1,
                "nivel_utilizacao": 1,
            },
        )
    )

    if not docs:
        return pd.DataFrame()

    df = pd.DataFrame(docs)
    df["common_name"] = df.get("common_name", "").fillna("")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["nivel_utilizacao"] = pd.Categorical(
        df["nivel_utilizacao"],
        categories=LEVEL_ORDER,
        ordered=True,
    )
    return df.sort_values(
        ["nivel_utilizacao", "common_name", "place_id"]
    ).reset_index(drop=True)


def build_map(df: pd.DataFrame, selected_timestamp: datetime | None) -> folium.Map:
    center = [df["lat"].mean(), df["lon"].mean()] if not df.empty else [51.5074, -0.1278]
    fmap = folium.Map(
        location=center,
        zoom_start=12,
        tiles="OpenStreetMap",
        width="100%",
        height=680,
    )

    for row in df.itertuples(index=False):
        marker_color = LEVEL_MARKER_COLORS.get(row.nivel_utilizacao, "gray")
        popup_html = f"""
        <b>{row.common_name or row.place_id}</b><br>
        <b>Place ID:</b> {row.place_id}<br>
        <b>Nivel:</b> {row.nivel_utilizacao}<br>
        <b>Bikes:</b> {row.bikes}<br>
        <b>Empty docks:</b> {row.empty_docks}<br>
        <b>Docks:</b> {row.docks}<br>
        <b>Timestamp:</b> {row.query_time:%Y-%m-%d %H:%M}
        """
        folium.Marker(
            location=[row.lat, row.lon],
            icon=folium.Icon(color=marker_color, icon="bicycle", prefix="fa"),
            tooltip=row.common_name or row.place_id,
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(fmap)

    if not df.empty:
        fmap.fit_bounds(df[["lat", "lon"]].to_numpy().tolist(), padding=(12, 12))

    timestamp_label = (
        selected_timestamp.strftime("%Y-%m-%d %H:%M") if pd.notna(selected_timestamp) else "-"
    )
    legend = """
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 9999;
        background: white;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 14px;
    ">
      <b>Nivel de utilizacao</b><br>
      <small>""" + timestamp_label + """</small><br><br>
      <span style="color:#f59e0b;">&#9679;</span> Frequente<br>
      <span style="color:#2f9e44;">&#9679;</span> Moderado<br>
      <span style="color:#d9480f;">&#9679;</span> Excessivo
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend))
    return fmap


def render_distribution(df: pd.DataFrame):
    counts = (
        df["nivel_utilizacao"]
        .value_counts()
        .reindex(LEVEL_ORDER, fill_value=0)
        .rename_axis("nivel_utilizacao")
        .reset_index(name="count")
    )
    st.vega_lite_chart(
        counts,
        {
            "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
            "encoding": {
                "x": {
                    "field": "nivel_utilizacao",
                    "type": "nominal",
                    "sort": LEVEL_ORDER,
                    "axis": {"title": None, "labelAngle": 0},
                },
                "y": {
                    "field": "count",
                    "type": "quantitative",
                    "axis": {"title": "Observacoes"},
                },
                "color": {
                    "field": "nivel_utilizacao",
                    "type": "nominal",
                    "scale": {
                        "domain": LEVEL_ORDER,
                        "range": [LEVEL_COLORS[level] for level in LEVEL_ORDER],
                    },
                    "legend": None,
                },
                "tooltip": [
                    {"field": "nivel_utilizacao", "type": "nominal", "title": "Nivel"},
                    {"field": "count", "type": "quantitative", "title": "Observacoes"},
                ],
            },
        },
        use_container_width=True,
    )


def render_table(df: pd.DataFrame):
    table_df = (
        df[
            [
                "common_name",
                "place_id",
                "query_time",
                "nivel_utilizacao",
                "bikes",
                "empty_docks",
                "docks",
                "lat",
                "lon",
            ]
        ]
        .rename(
            columns={
                "common_name": "Estacao",
                "place_id": "Place ID",
                "query_time": "Timestamp",
                "nivel_utilizacao": "Nivel",
                "bikes": "Bikes",
                "empty_docks": "Empty docks",
                "docks": "Docks",
                "lat": "Latitude",
                "lon": "Longitude",
            }
        )
        .copy()
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)


st.title("London Bikes Dashboard")
st.caption("Exploracao interativa da collection bikes_modelled_summer em MongoDB.")

try:
    _, connected_uri = get_database()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

available_dates = get_available_dates()
if not available_dates:
    st.warning("Nao foram encontradas datas na collection bikes_modelled_summer.")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    st.caption(f"MongoDB ativo em: `{connected_uri}`")

    selected_date = st.selectbox(
        "Data",
        options=available_dates,
        index=min(29, len(available_dates) - 1),
    )
    available_hours = get_available_hours(selected_date)
    if not available_hours:
        st.warning("Nao existem horas disponiveis para a data selecionada.")
        st.stop()

    default_hour_index = available_hours.index(14) if 14 in available_hours else 0
    selected_hour = st.selectbox(
        "Hora",
        options=available_hours,
        index=default_hour_index,
    )

    available_minutes = get_available_minutes(selected_date, selected_hour)
    if not available_minutes:
        st.warning("Nao existem minutos disponiveis para a hora selecionada.")
        st.stop()

    default_minute_index = available_minutes.index(0) if 0 in available_minutes else 0
    selected_minute = st.selectbox(
        "Minuto",
        options=available_minutes,
        index=default_minute_index,
    )

    st.markdown("**Nivel de utilizacao**")
    selected_levels = []
    for level in LEVEL_ORDER:
        st.markdown(
            f"<span style='color:{LEVEL_COLORS[level]}; font-size: 0.95rem;'><b>{level}</b></span>",
            unsafe_allow_html=True,
        )
        is_selected = st.checkbox(
            f"Selecionar {level}",
            value=True,
            key=f"level_{level}",
            label_visibility="collapsed",
        )
        if is_selected:
            selected_levels.append(level)

    if not selected_levels:
        st.warning("Seleciona pelo menos um nivel de utilizacao.")
        st.stop()

    st.markdown("**Descricao dos niveis**")
    for level in LEVEL_ORDER:
        st.markdown(
            f"<span style='color:{LEVEL_COLORS[level]};'><b>{level}</b></span>: {LEVEL_DESCRIPTIONS[level]}",
            unsafe_allow_html=True,
        )

snapshot_df = load_snapshot(selected_date, selected_hour, selected_minute)
if snapshot_df.empty:
    st.warning("Nao existem observacoes para a combinacao selecionada.")
    st.stop()

filtered_df = snapshot_df[snapshot_df["nivel_utilizacao"].isin(selected_levels)].copy()
map_df = filtered_df.dropna(subset=["lat", "lon"]).copy()

selected_timestamp = filtered_df["query_time"].min() if "query_time" in filtered_df.columns else None
if pd.notna(selected_timestamp):
    st.caption(f"Janela temporal selecionada: {selected_timestamp:%Y-%m-%d %H:%M}")

if filtered_df.empty:
    st.warning("Nao existem observacoes para os niveis de utilizacao selecionados.")
    st.stop()

metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Observacoes", f"{len(filtered_df):,}")
metric_2.metric("Estacoes distintas", f"{filtered_df['place_id'].nunique():,}")
metric_3.metric("Media bikes", f"{filtered_df['bikes'].mean():.1f}")
metric_4.metric("Media empty docks", f"{filtered_df['empty_docks'].mean():.1f}")

st.subheader("Mapa")
if map_df.empty:
    st.warning("Nao existem coordenadas disponiveis para renderizar o mapa neste instante.")
else:
    map_html = build_map(map_df, selected_timestamp).get_root().render()
    components.html(map_html, height=720, scrolling=False)

stats_left_col, stats_right_col = st.columns([1.2, 1])

with stats_left_col:
    st.subheader("Distribuicao por nivel")
    render_distribution(filtered_df)

with stats_right_col:
    st.subheader("Resumo")
    summary_df = (
        filtered_df.groupby("nivel_utilizacao", observed=False)
        .agg(
            observacoes=("place_id", "size"),
            bikes_medias=("bikes", "mean"),
            empty_docks_medias=("empty_docks", "mean"),
            docks_medias=("docks", "mean"),
        )
        .reindex(LEVEL_ORDER)
        .fillna(0)
    )
    st.dataframe(summary_df.round(2), use_container_width=True)

st.subheader("Tabela de estacoes")
render_table(filtered_df)
