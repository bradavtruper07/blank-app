import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd

# Configuración de la página
st.set_page_config(
    page_title="Exploración GLM Risk Load",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título
st.title("Dashboard Exploratorio: Risk Load - GLM Tarificación")

# Carga de datos
@st.cache_data
def load_data():
    df = pd.read_excel("base_agrup.xlsx", sheet_name="kmeans_com_ward")
    # Variables agrupadas de interés
    grp_vars = ["numst_group", "year_band", "cluster_geo"]
    # Eliminar columnas irrelevantes
    cols_drop = ["accgrpid", "streetname", "addrmatch", "numstories", "year_built", "occtype"]
    df = df.drop(columns=[c for c in cols_drop if c in df.columns])
    return df

df = load_data()

# Sidebar: selección de sección
section = st.sidebar.radio(
    "Sección:",
    ["Visión General", "Univariada", "Bivariada", "Mapa Interactivo"]
)

if section == "Visión General":
    st.header("Visión General de los Datos")
    st.write(f"Número de observaciones: {df.shape[0]}")
    st.write(f"Número de variables: {df.shape[1]}")
    st.dataframe(df.head(20))
    st.subheader("Estadísticas Descriptivas")
    st.dataframe(df.describe(include='all').T)

elif section == "Univariada":
    st.header("Análisis Univariado")
    grp_vars = ["numst_group", "year_band", "cluster_geo", "occtype_grp_w"]
    var = st.selectbox(
        "Elige variable:",
        grp_vars + df.select_dtypes(include='number').columns.tolist()
    )
    if df[var].dtype in ['object', 'category']:
        fig = px.histogram(df, x=var, color=var, title=f"Distribución de {var}")
    else:
        fig = px.histogram(df, x=var, nbins=30, title=f"Distribución de {var}")
    st.plotly_chart(fig, use_container_width=True)

elif section == "Bivariada":
    st.header("Análisis Bivariado")
    grp_vars = ["numst_group", "year_band", "cluster_geo", "occtype_grp_w"]
    x_var = st.selectbox(
        "Eje X:",
        grp_vars + df.select_dtypes(include='number').columns.tolist(),
        index=0
    )
    y_var = st.selectbox(
        "Eje Y:",
        [v for v in df.select_dtypes(include='number').columns if v != x_var],
        index=0
    )
    fig = px.scatter(
        df, x=x_var, y=y_var, color="cluster_geo",
        title=f"Relación: {x_var} vs {y_var}"
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.header("Mapa Interactivo de Cuentas Aseguradas")

    # URLs de GeoJSON oficiales/publicados en GitHub
    URL_REGIONES = (
        "https://raw.githubusercontent.com/robertoflores/chile-geodata/"
        "master/regiones.geojson"
    )
    URL_COMUNAS = (
        "https://raw.githubusercontent.com/robertoflores/chile-geodata/"
        "master/comunas.geojson"
    )

    try:
        gdf_reg = gpd.read_file(URL_REGIONES)
        gdf_comm = gpd.read_file(URL_COMUNAS)

        # Mapa por Región
        st.subheader("Cuentas por Región")
        df_reg = df.groupby("cluster_geo").size().reset_index(name="counts")
        fig_reg = px.choropleth_mapbox(
            df_reg,
            geojson=gdf_reg,
            locations="cluster_geo",
            featureidkey="properties.region_id",
            color="counts",
            mapbox_style="carto-positron",
            zoom=4,
            center={"lat": -33.5, "lon": -70.7},
            title="Cuentas por Región"
        )
        st.plotly_chart(fig_reg, use_container_width=True)

        # Mapa Región Metropolitana (por comuna)
        st.subheader("Región Metropolitana: distrib. por comuna")
        # Filtrar comuna RM
        rm_comm = gdf_comm[gdf_comm["properties"]["region_name"] == "Región Metropolitana"]
        # Renombrar clave comuna para merge
        df_comm = df[df["cluster_geo"] == "RM"].groupby("occtype_grp_w").size().reset_index(name="counts")
        # Suponiendo que 'occtype_grp_w' coincide con 'properties.comuna_id'
        rm_comm = rm_comm.set_index("properties.comuna_id").join(
            df_comm.set_index("occtype_grp_w"), how="left").fillna(0).reset_index()
        fig_comm = px.choropleth_mapbox(
            rm_comm,
            geojson=rm_comm,
            locations="properties.comuna_id",
            featureidkey="properties.comuna_id",
            color="counts",
            mapbox_style="carto-positron",
            zoom=10,
            center={"lat": -33.45, "lon": -70.65},
            title="Cuentas RM por Occtype"
        )
        st.plotly_chart(fig_comm, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar mapas desde URLs: {e}")

# Footer
st.markdown("---")
st.caption("Aplicación Streamlit para exploración de Risk Load con mapas en vivo")

### How to run it on your own machine

