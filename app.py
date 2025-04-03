import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import load_noise_data, load_sensor_locations, merge_noise_and_locations, compute_voronoi

# Carreguem les dades
df_locs = load_sensor_locations("data/noise_stations.csv")
df_noise = load_noise_data("data/noise_data.csv")
df = merge_noise_and_locations(df_noise, df_locs)

# Marquem si una estació té dades associades
stations_with_data = df_noise["Id_Instal"].unique()
df_locs["has_data"] = df_locs["Id_Instal"].isin(stations_with_data)

# Inicialitzem l’app
app = dash.Dash(__name__)
app.title = "Soroll a Barcelona"

# ------------------------
# Mapa amb Voronoi
# ------------------------
fig_map = px.scatter_mapbox(
    df_locs,
    lat="Latitud",
    lon="Longitud",
    color="has_data",
    color_discrete_map={True: "green", False: "red"},
    hover_name="Id_Instal",
    hover_data=["Nom_Barri", "Nom_Districte"],
    zoom=11,
    height=600
)
fig_map.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})

# Calculem Voronoi i l'afegim
vor, vor_lines_lonlat = compute_voronoi(df_locs)
lats, lons = [], []
for line in vor_lines_lonlat:
    lons.extend([line[0][0], line[1][0], None])
    lats.extend([line[0][1], line[1][1], None])
fig_map.add_trace(go.Scattermapbox(
    lat=lats,
    lon=lons,
    mode="lines",
    line=dict(color="black", width=1),
    hoverinfo="skip",
    showlegend=False
))

# ------------------------
# Tile map: nivell mitjà de soroll
# ------------------------
df_avg = df.groupby("Id_Instal").agg({
    "Nivell_LAeq_1h": "mean",
    "Latitud": "first",
    "Longitud": "first"
}).reset_index()

fig_tiles = px.scatter_mapbox(
    df_avg,
    lat="Latitud",
    lon="Longitud",
    color="Nivell_LAeq_1h",
    color_continuous_scale="YlOrRd",
    size_max=15,
    zoom=11,
    height=600,
    hover_name="Id_Instal",
    labels={"Nivell_LAeq_1h": "Soroll mitjà (dB)"}
)
fig_tiles.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})

# ------------------------
# Layout amb selector
# ------------------------
app.layout = html.Div([
    html.H2("Visualització de soroll a Barcelona"),

    dcc.RadioItems(
        id="mapa_selector",
        options=[
            {"label": "Mapa d'estacions + Voronoi", "value": "voronoi"},
            {"label": "Tile map - soroll mitjà", "value": "tile"}
        ],
        value="voronoi",
        labelStyle={"display": "inline-block", "margin-right": "20px"},
        style={"margin-bottom": "20px"}
    ),

    dcc.Graph(id="mapa_dinamica"),
    html.Div(id="sensor_seleccionat", style={"fontSize": "20px", "marginTop": "20px"}),
    html.Div(id="heatmap-output", style={"marginTop": "40px"})
])

# ------------------------
# Callback: canvi de mapa
# ------------------------
@app.callback(
    Output("mapa_dinamica", "figure"),
    Input("mapa_selector", "value")
)
def mostrar_mapa_tipus(tipus):
    if tipus == "tile":
        return fig_tiles
    else:
        return fig_map

# ------------------------
# Callback: selecció d’estació
# ------------------------
@app.callback(
    Output("sensor_seleccionat", "children"),
    Input("mapa_dinamica", "clickData"),
    Input("mapa_selector", "value")
)
def mostrar_sensor(clickData, tipus):
    if tipus == "tile":
        return "Mode tile map activat"
    if clickData is None:
        return "No s'ha seleccionat cap estació"
    sensor_id = clickData["points"][0]["hovertext"]
    return f"Estació seleccionada: {sensor_id}"

# ------------------------
# Callback: heatmap del sensor
# ------------------------
@app.callback(
    Output("heatmap-output", "children"),
    Input("mapa_dinamica", "clickData"),
    Input("mapa_selector", "value"),
    prevent_initial_call=True
)
def mostrar_heatmap(clickData, tipus):
    if tipus == "tile" or clickData is None:
        return dash.no_update

    sensor_id = int(clickData["points"][0]["hovertext"])
    df_sel = df[df["Id_Instal"] == sensor_id]

    if df_sel.empty:
        return html.Div("No hi ha dades per a aquesta estació.", style={"color": "red"})

    df_sel["Dia"] = df_sel["Datetime"].dt.date
    df_sel["Hora"] = df_sel["Datetime"].dt.strftime("%H:%M")

    pivot = df_sel.pivot(index="Dia", columns="Hora", values="Nivell_LAeq_1h")
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)

    fig_heatmap = px.imshow(
        pivot,
        labels=dict(x="Hora", y="Dia", color="LAeq (dB)"),
        aspect="auto",
        color_continuous_scale="YlOrRd",
        title=f"Mapa de calor horari - Estació {sensor_id}",
        height=900
    )

    return dcc.Graph(figure=fig_heatmap)

# ------------------------
# Execució
# ------------------------
if __name__ == "__main__":
    app.run(debug=True)
