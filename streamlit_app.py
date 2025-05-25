import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
import io

# ----------------------
#     Configuración
# ----------------------
st.set_page_config(
    page_title="Exploratorio Risk Load",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    df = pd.read_excel("base_agrup.xlsx", sheet_name="kmeans_com_ward")
    # Eliminamos columnas irrelevantes
    drop_cols = ["accgrpid","streetname","addrmatch","numstories","year_built","region","occtype"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    # Convertir variables agrupadas a categoría
    for c in ["numst_group","year_band","cluster_geo","occtype_grp"]:
        if c in df.columns:
            df[c] = df[c].astype('category')
    return df

df = load_data()

# Cargar GeoJSON de regiones y comunas
@st.cache_data
def load_geodata():
    url_reg = "https://raw.githubusercontent.com/robertoflores/chile-geodata/master/regiones.geojson"
    url_com = "https://raw.githubusercontent.com/robertoflores/chile-geodata/master/comunas.geojson"
    gdf_reg = gpd.read_file(url_reg)
    gdf_com = gpd.read_file(url_com)
    return gdf_reg, gdf_com

gdf_reg, gdf_com = load_geodata()

# Sidebar
st.sidebar.title("Menú")
section = st.sidebar.radio("Sección:",
    ["Visión General","Univariada","Bivariada","Correlación","Mapa Regiones","Mapa Comunas RM"]
)

# ----------------------
#  Visión General
# ----------------------
if section == "Visión General":
    st.title("Visión General de la Base de Datos")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Observaciones", df.shape[0])
        st.metric("Variables", df.shape[1])
    with col2:
        st.dataframe(df.head(10))
    st.markdown("---")
    st.subheader("Estadísticas Descriptivas")
    st.dataframe(df.describe(include='all').T)

# ----------------------
#  Univariada
# ----------------------
elif section == "Univariada":
    st.title("Análisis Univariado")
    var = st.selectbox("Seleccionar variable:", df.columns.tolist())
    if str(df[var].dtype) == 'category':
        ct = df[var].value_counts().reset_index()
        ct.columns = [var, 'count']
        ct['prop'] = (ct['count']/ct['count'].sum()).round(3)
        fig = px.bar(ct, x=var, y='count', text='prop', title=f"Distribución de {var}", color=var)
    else:
        fig = px.histogram(df, x=var, nbins=30, marginal="box", title=f"Histograma y Boxplot de {var}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------
#  Bivariada
# ----------------------
elif section == "Bivariada":
    st.title("Análisis Bivariado")
    num_cols = df.select_dtypes(include='number').columns.tolist()
    x_var = st.selectbox("Eje X:", num_cols)
    y_var = st.selectbox("Eje Y:", [c for c in num_cols if c!=x_var])
    cat_cols = df.select_dtypes(['category']).columns.tolist()
    color_var = st.selectbox("Color:", cat_cols)
    fig = px.scatter(df, x=x_var, y=y_var, color=color_var, trendline="ols",
                     title=f"Scatter: {x_var} vs {y_var}")
    st.plotly_chart(fig, use_container_width=True)

# ----------------------
#  Correlación
# ----------------------
elif section == "Correlación":
    st.title("Mapa de Calor de Correlaciones")
    corr = df.select_dtypes(include='number').corr()
    fig, ax = plt.subplots(figsize=(10,8))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
    st.pyplot(fig)


# ----------------------
#  Mapas
# ----------------------
elif section == "Mapas":
    st.title("Mapas Espaciales Automáticos")
    # URLs GeoJSON de Caracena
    url_reg = "https://raw.githubusercontent.com/caracena/chile-geojson/master/regiones.json"
    url_com = "https://raw.githubusercontent.com/caracena/chile-geojson/master/comunas.json"
    try:
        gdf_reg = gpd.read_file(url_reg)
        gdf_com = gpd.read_file(url_com)
    except Exception as e:
        st.error(f"Error cargando GeoJSON: {e}")
        st.stop()

    # Choropleth: recargo promedio por región
    st.subheader("Recargo Promedio por Región")
    df_reg = df.groupby("cluster_geo").agg(
        cuentas=("risk_load","size"),
        recargo_avg=("risk_load","mean")
    ).reset_index()
    gdf_reg = gdf_reg.merge(df_reg, left_on="properties.region_id", right_on="cluster_geo", how="left").fillna({
        "cuentas":0, "recargo_avg":0
    })
    fig1 = px.choropleth_mapbox(
        gdf_reg,
        geojson=gdf_reg.geometry,
        locations=gdf_reg.index,
        color="recargo_avg",
        hover_name="properties.region_name",
        hover_data=["cuentas","recargo_avg"],
        mapbox_style="carto-positron",
        zoom=4,
        center={"lat":-33.5, "lon":-70.7},
        opacity=0.7,
        title="Recargo Promedio por Región"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Choropleth: AAL promedio por región
    st.subheader("AAL Promedio por Región")
    df_reg2 = df.groupby("cluster_geo").agg(
        AAL_avg=("AAL_usd","mean")
    ).reset_index()
    gdf_reg2 = gdf_reg.merge(df_reg2, on="cluster_geo", how="left").fillna({"AAL_avg":0})
    fig2 = px.choropleth_mapbox(
        gdf_reg2,
        geojson=gdf_reg2.geometry,
        locations=gdf_reg2.index,
        color="AAL_avg",
        hover_name="properties.region_name",
        hover_data=["AAL_avg"],
        mapbox_style="carto-positron",
        zoom=4,
        center={"lat":-33.5, "lon":-70.7},
        opacity=0.7,
        title="AAL Promedio por Región"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Choropleth: recargo promedio por comuna en RM
    st.subheader("Recargo Promedio por Comuna (RM)")
    rm_com = gdf_com[gdf_com['properties']['region_name']=="Región Metropolitana"].copy()
    if 'city' in df.columns:
        df_com = df.groupby('city').agg(
            cuentas=('risk_load','size'),
            recargo_avg=('risk_load','mean')
        ).reset_index()
        rm_com = rm_com.merge(df_com, left_on='properties.comuna_id', right_on='city', how='left').fillna({
            'cuentas':0, 'recargo_avg':0
        })
        fig3 = px.choropleth_mapbox(
            rm_com,
            geojson=rm_com.geometry,
            locations=rm_com.index,
            color='recargo_avg',
            hover_name='properties.comuna_name',
            hover_data=['cuentas','recargo_avg'],
            mapbox_style='carto-positron',
            zoom=10,
            center={'lat':-33.45,'lon':-70.65},
            opacity=0.7,
            title='Recargo Promedio por Comuna (Región Metropolitana)'
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Agrega columna 'city' para mapear comunas en RM.")

# ----------------------
#    Footer
# ----------------------
st.markdown("---")
st.caption("Dashboard interactivo para exploración de Risk Load")
