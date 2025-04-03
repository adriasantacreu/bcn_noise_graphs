import pandas as pd
from scipy.spatial import Voronoi
import pyproj
import numpy as np

def load_noise_data(filepath_noise):
    df = pd.read_csv(filepath_noise)
    df['Hora_num'] = df['Hora'].str.extract(r'(\d+):').astype(int)
    df['Datetime'] = pd.to_datetime(df['Any'].astype(str) + '-' +
                                    df['Mes'].astype(str).str.zfill(2) + '-' +
                                    df['Dia'].astype(str).str.zfill(2) + ' ' +
                                    df['Hora'])
    return df

def load_sensor_locations(filepath_locations):
    df = pd.read_csv(filepath_locations)
    df = df[['Id_Instal', 'Latitud', 'Longitud', 'Nom_Barri', 'Nom_Districte']]
    return df

def merge_noise_and_locations(df_noise, df_locations):
    return df_noise.merge(df_locations, on='Id_Instal', how='left')

def compute_voronoi(df_locations):
    # Projectem coordenades geogràfiques a UTM per al Voronoi
    proj_wgs84 = pyproj.CRS("EPSG:4326")
    proj_utm = pyproj.CRS("EPSG:25831")  # UTM zona 31N, per Barcelona
    transformer_to_utm = pyproj.Transformer.from_crs(proj_wgs84, proj_utm, always_xy=True)
    transformer_to_wgs = pyproj.Transformer.from_crs(proj_utm, proj_wgs84, always_xy=True)

    # Converteix les coordenades geogràfiques a UTM
    coords_utm = np.array([transformer_to_utm.transform(lon, lat)
                           for lon, lat in df_locations[['Longitud', 'Latitud']].values])

    vor = Voronoi(coords_utm)

    # Generem línies Voronoi transformades de nou a lon/lat
    voronoi_lines = []
    for vpair in vor.ridge_vertices:
        if -1 in vpair:
            continue
        p0 = vor.vertices[vpair[0]]
        p1 = vor.vertices[vpair[1]]
        lonlat0 = transformer_to_wgs.transform(p0[0], p0[1])
        lonlat1 = transformer_to_wgs.transform(p1[0], p1[1])
        voronoi_lines.append([(lonlat0[0], lonlat0[1]), (lonlat1[0], lonlat1[1])])

    return vor, voronoi_lines