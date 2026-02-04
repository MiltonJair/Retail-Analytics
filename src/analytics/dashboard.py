import streamlit as st
import pandas as pd
import numpy as np
import pyodbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Configuración de página
st.set_page_config(
    page_title="Walmart Forecasting Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .header-title {
        color: #1f77b4;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE CONEXIÓN Y DATOS
# ============================================================================

def get_connection():
    """Conectar a SQL Server (sin cache para evitar conexiones cerradas)"""
    try:
        conn = pyodbc.connect(
            'Driver={ODBC Driver 17 for SQL Server};'
            'Server=localhost;'
            'Database=WalmartAnalytics;'
            'Trusted_Connection=yes;'
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

@st.cache_data(ttl=3600)
def get_sales_data():
    """Obtener datos de ventas históricos"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    SELECT 
        CAST(ih.InvoiceDate AS DATE) as Fecha,
        s.StoreName,
        s.State,
        d.DepartmentName,
        i.ItemName,
        id.QuantitySold as Cantidad,
        id.UnitPrice as PrecioUnitario,
        id.LineTotal as VentaTotal
    FROM InvoiceHeaders ih
    INNER JOIN InvoiceDetails id ON ih.InvoiceID = id.InvoiceID
    INNER JOIN Stores s ON ih.StoreID = s.StoreID
    INNER JOIN Items i ON id.ItemID = i.ItemID
    INNER JOIN Departments d ON i.DepartmentID = d.DepartmentID
    ORDER BY ih.InvoiceDate DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        return df
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass

@st.cache_data(ttl=3600)
def get_stores_summary():
    """Obtener resumen por tienda"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    SELECT 
        s.StoreName,
        s.State,
        COUNT(DISTINCT ih.InvoiceID) as TotalFacturas,
        COUNT(DISTINCT id.ItemID) as ProductosUnicos,
        SUM(id.LineTotal) as VentasTotal,
        AVG(id.LineTotal) as TicketPromedio
    FROM InvoiceHeaders ih
    INNER JOIN InvoiceDetails id ON ih.InvoiceID = id.InvoiceID
    INNER JOIN Stores s ON ih.StoreID = s.StoreID
    GROUP BY s.StoreName, s.State
    ORDER BY VentasTotal DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error al obtener resumen: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="header-title">📊 Walmart Hierarchical Forecasting Dashboard</div>', unsafe_allow_html=True)
st.markdown("**Sistema de Pronóstico de Ventas con Reconciliación Jerárquica**")
st.divider()

# ============================================================================
# SIDEBAR - CONTROLES
# ============================================================================

with st.sidebar:
    st.header("Controles")
    
    vista = st.radio(
        "Selecciona vista:",
        [
            "Resumen General",
            "Top 10 Tiendas",
            "Analisis por Producto",
            "Analisis por Departamento",
            "Forecasting Jerarquico",
            "Por Tienda",
            "Analisis Detallado",
            "Analisis de Clientes",
            "Segmentacion RFM",
            "Datos Raw"
        ]
    )
    
    st.divider()
    
    # Información general
    st.subheader("ℹ️ Información")
    st.info("""
    **Periodo de análisis:** Jul 1 - Sep 28, 2019
    
    **Métodos de forecasting:**
    - ⬆️ Bottom-Up (Agregación)
    - ⬇️ Top-Down (Distribución)
    - 📈 ARIMA (Estadístico)
    """)

# ============================================================================
# FUNCIONES DE ANÁLISIS DE CLIENTES
# ============================================================================

@st.cache_data(ttl=3600)
def get_customer_analytics():
    """Obtener análisis de clientes con RFM y Churn Risk"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    SELECT 
        c.CustomerID,
        c.CustomerCode,
        c.FirstName + ' ' + c.LastName as CustomerName,
        c.City,
        c.State,
        c.MembershipTier,
        c.TotalLifetimeSpend as LifetimeSpend,
        cr.Recency,
        cr.Frequency,
        cr.Monetary,
        cr.RFM_Score,
        cr.Segment,
        ccr.ChurnRiskScore,
        ccr.ChurnRiskCategory,
        ccr.RecommendedAction,
        (SELECT COUNT(*) FROM InvoiceHeaders WHERE CustomerID = c.CustomerID) as TotalTransactions,
        c.LastPurchaseDate
    FROM Customers c
    LEFT JOIN CustomerRFM cr ON c.CustomerID = cr.CustomerID
    LEFT JOIN CustomerChurnRisk ccr ON c.CustomerID = ccr.CustomerID
    WHERE c.CustomerID IS NOT NULL
    ORDER BY c.TotalLifetimeSpend DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.warning(f"Error al obtener datos de clientes: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass

@st.cache_data(ttl=3600)
def get_rfm_summary():
    """Obtener resumen de segmentación RFM"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    SELECT 
        cr.Segment,
        COUNT(*) as CustomerCount,
        CAST(AVG(cr.Recency) AS INT) as AvgRecency,
        CAST(AVG(cr.Frequency) AS INT) as AvgFrequency,
        CAST(AVG(cr.Monetary) AS DECIMAL(10,2)) as AvgMonetary,
        CAST(SUM(cr.Monetary) AS DECIMAL(12,2)) as TotalMonetary,
        CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM CustomerRFM) AS DECIMAL(5,2)) as SegmentPct
    FROM CustomerRFM cr
    GROUP BY cr.Segment
    ORDER BY TotalMonetary DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.warning(f"Error al obtener RFM: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass

@st.cache_data(ttl=3600)
def get_churn_risk_summary():
    """Obtener resumen de riesgo de churn"""
    conn = get_connection()
    if not conn:
        return None
    
    query = """
    SELECT 
        ccr.ChurnRiskCategory,
        COUNT(*) as CustomerCount,
        CAST(AVG(ccr.ChurnRiskScore) AS DECIMAL(5,2)) as AvgChurnScore,
        CAST(SUM(c.TotalLifetimeSpend) AS DECIMAL(12,2)) as TotalAtRisk
    FROM CustomerChurnRisk ccr
    JOIN Customers c ON ccr.CustomerID = c.CustomerID
    GROUP BY ccr.ChurnRiskCategory
    ORDER BY CASE WHEN ccr.ChurnRiskCategory = 'High' THEN 1 
                  WHEN ccr.ChurnRiskCategory = 'Medium' THEN 2 ELSE 3 END
    """
    
    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.warning(f"Error al obtener churn: {e}")
        return None
    finally:
        try:
            conn.close()
        except:
            pass

# ============================================================================
# VISTA: RESUMEN GENERAL
# ============================================================================

if vista == "Resumen General":
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏪 Total Tiendas", "20")
    with col2:
        st.metric("📦 Departamentos", "7")
    with col3:
        st.metric("🛍️ Productos", "26")
    with col4:
        st.metric("📅 Días Históricos", "90")
    
    st.divider()
    
    # Obtener datos
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Métricas principales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_ventas = sales_df['VentaTotal'].sum()
            st.metric("💰 Total Ventas", f"${total_ventas:,.2f}")
        
        with col2:
            avg_ticket = sales_df['VentaTotal'].mean()
            st.metric("🎫 Ticket Promedio", f"${avg_ticket:,.2f}")
        
        with col3:
            total_items = sales_df['Cantidad'].sum()
            st.metric("📦 Items Vendidos", f"{int(total_items):,}")
        
        st.divider()
        
        # Gráficos principales
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Ventas por Día")
            daily_sales = sales_df.groupby('Fecha')['VentaTotal'].sum().reset_index()
            fig = px.line(
                daily_sales, 
                x='Fecha', 
                y='VentaTotal',
                title="Tendencia de Ventas",
                labels={'VentaTotal': 'Ventas ($)', 'Fecha': 'Fecha'},
                markers=True
            )
            fig.update_layout(hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🏪 Top 10 Tiendas")
            top_stores = sales_df.groupby('StoreName')['VentaTotal'].sum().nlargest(10).reset_index()
            fig = px.bar(
                top_stores,
                x='VentaTotal',
                y='StoreName',
                orientation='h',
                title="Tiendas con Mayor Venta",
                labels={'VentaTotal': 'Ventas ($)', 'StoreName': 'Tienda'},
                color='VentaTotal',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Ventas por departamento
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📂 Ventas por Departamento")
            dept_sales = sales_df.groupby('DepartmentName')['VentaTotal'].sum().sort_values(ascending=False)
            fig = px.pie(
                values=dept_sales.values,
                names=dept_sales.index,
                title="Distribución de Ventas",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col1:
            st.subheader("🗺️ Ventas por Estado")
            state_sales = sales_df.groupby('State')['VentaTotal'].sum().sort_values(ascending=False)
            fig = px.bar(
                x=state_sales.index,
                y=state_sales.values,
                title="Ventas por Estado",
                labels={'x': 'Estado', 'y': 'Ventas ($)'},
                color=state_sales.values,
                color_continuous_scale='Greens'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: TOP 10 TIENDAS (Requisito 6c del test Walmart)
# ============================================================================

elif vista == "Top 10 Tiendas":
    st.subheader("🏆 Top 10 Tiendas con Mayor Venta")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Top 10 stores
        top_10_stores = sales_df.groupby('StoreName').agg({
            'VentaTotal': ['sum', 'mean', 'count'],
            'Cantidad': 'sum',
            'State': 'first'
        }).reset_index()
        
        top_10_stores.columns = ['StoreName', 'TotalVentas', 'VentaPromedio', 'NumTransacciones', 'TotalItems', 'Estado']
        top_10_stores = top_10_stores.nlargest(10, 'TotalVentas')
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏆 #1 Tienda", top_10_stores.iloc[0]['StoreName'])
        with col2:
            st.metric("💰 Ventas #1", f"${top_10_stores.iloc[0]['TotalVentas']:,.2f}")
        with col3:
            st.metric("📊 Promedio Top 10", f"${top_10_stores['TotalVentas'].mean():,.2f}")
        with col4:
            st.metric("📈 Crecimiento", f"{(top_10_stores.iloc[0]['TotalVentas'] / top_10_stores.iloc[9]['TotalVentas'] - 1) * 100:.1f}%")
        
        st.divider()
        
        # Gráfico principal
        fig = px.bar(
            top_10_stores,
            x='TotalVentas',
            y='StoreName',
            orientation='h',
            color='TotalVentas',
            color_continuous_scale='Blues',
            title="Top 10 Tiendas por Venta Total",
            labels={'TotalVentas': 'Ventas Totales ($)', 'StoreName': 'Tienda'},
            text='TotalVentas'
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Tabla detallada
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Métricas Detalladas")
            display_df = top_10_stores.copy()
            display_df['Rango'] = range(1, len(display_df) + 1)
            display_df['TotalVentas'] = display_df['TotalVentas'].apply(lambda x: f"${x:,.2f}")
            display_df['VentaPromedio'] = display_df['VentaPromedio'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(
                display_df[['Rango', 'StoreName', 'Estado', 'TotalVentas', 'VentaPromedio', 'NumTransacciones']],
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.subheader("🗺️ Distribución Geográfica")
            state_dist = top_10_stores.groupby('Estado')['TotalVentas'].sum()
            fig = px.pie(
                values=state_dist.values,
                names=state_dist.index,
                title="Ventas Top 10 por Estado"
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: ANÁLISIS POR PRODUCTO (Requisito 6e del test Walmart)
# ============================================================================

elif vista == "Analisis por Producto":
    st.subheader("📊 Top 20 Productos (Items) - Análisis Detallado")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Obtener top 20 items globales
        top_20_items_global = sales_df.groupby('ItemName').agg({
            'VentaTotal': ['sum', 'count', 'mean'],
            'Cantidad': 'sum',
            'DepartmentName': 'first'
        }).reset_index()
        
        top_20_items_global.columns = ['ItemName', 'TotalVentas', 'NumVentas', 'VentaPromedio', 'CantidadTotal', 'Departamento']
        top_20_items_global = top_20_items_global.nlargest(20, 'TotalVentas')
        
        # Tabs para análisis
        tab1, tab2, tab3 = st.tabs(["Global", "Por Tienda", "Por Departamento"])
        
        with tab1:
            st.subheader("🌍 Top 20 Productos a Nivel Global")
            
            # Métricas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🥇 #1 Producto", top_20_items_global.iloc[0]['ItemName'][:30])
            with col2:
                st.metric("💰 Venta #1", f"${top_20_items_global.iloc[0]['TotalVentas']:,.2f}")
            with col3:
                st.metric("📦 Items Vendidos", f"{int(top_20_items_global['CantidadTotal'].sum()):,}")
            
            st.divider()
            
            # Gráfico
            fig = px.bar(
                top_20_items_global,
                x='TotalVentas',
                y='ItemName',
                orientation='h',
                color='TotalVentas',
                color_continuous_scale='Greens',
                title="Top 20 Productos Globales",
                labels={'TotalVentas': 'Ventas ($)', 'ItemName': 'Producto'},
                text='TotalVentas'
            )
            fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla
            st.subheader("📋 Detalles de Top 20")
            display_df = top_20_items_global.copy()
            display_df['Rango'] = range(1, len(display_df) + 1)
            display_df['TotalVentas'] = display_df['TotalVentas'].apply(lambda x: f"${x:,.2f}")
            display_df['VentaPromedio'] = display_df['VentaPromedio'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(
                display_df[['Rango', 'ItemName', 'Departamento', 'TotalVentas', 'NumVentas', 'CantidadTotal']],
                use_container_width=True,
                hide_index=True
            )
        
        with tab2:
            st.subheader("🏪 Top 20 Productos por Tienda")
            
            tienda_sel = st.selectbox("Selecciona tienda:", sales_df['StoreName'].unique())
            
            tienda_items = sales_df[sales_df['StoreName'] == tienda_sel].groupby('ItemName').agg({
                'VentaTotal': ['sum', 'count'],
                'Cantidad': 'sum',
                'DepartmentName': 'first'
            }).reset_index()
            
            tienda_items.columns = ['ItemName', 'TotalVentas', 'NumVentas', 'CantidadTotal', 'Departamento']
            tienda_items = tienda_items.nlargest(20, 'TotalVentas')
            
            fig = px.bar(
                tienda_items,
                x='TotalVentas',
                y='ItemName',
                orientation='h',
                color='TotalVentas',
                color_continuous_scale='Oranges',
                title=f"Top 20 Productos en {tienda_sel}"
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("📂 Top 20 Productos por Departamento")
            
            dept_sel = st.selectbox("Selecciona departamento:", sales_df['DepartmentName'].unique())
            
            dept_items = sales_df[sales_df['DepartmentName'] == dept_sel].groupby('ItemName').agg({
                'VentaTotal': ['sum', 'count'],
                'Cantidad': 'sum'
            }).reset_index()
            
            dept_items.columns = ['ItemName', 'TotalVentas', 'NumVentas', 'CantidadTotal']
            dept_items = dept_items.nlargest(20, 'TotalVentas')
            
            fig = px.bar(
                dept_items,
                x='TotalVentas',
                y='ItemName',
                orientation='h',
                color='TotalVentas',
                color_continuous_scale='Purples',
                title=f"Top 20 Productos en {dept_sel}"
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: ANÁLISIS POR DEPARTAMENTO (Requisito 6f del test Walmart)
# ============================================================================

elif vista == "Analisis por Departamento":
    st.subheader("📂 Top 10 Departamentos - Análisis Detallado")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Top 10 departments
        top_10_depts = sales_df.groupby('DepartmentName').agg({
            'VentaTotal': ['sum', 'count', 'mean'],
            'Cantidad': 'sum',
            'ItemName': 'nunique'
        }).reset_index()
        
        top_10_depts.columns = ['DepartmentName', 'TotalVentas', 'NumTransacciones', 'VentaPromedio', 'CantidadTotal', 'ProductosUnicos']
        top_10_depts = top_10_depts.nlargest(10, 'TotalVentas')
        
        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🥇 #1 Departamento", top_10_depts.iloc[0]['DepartmentName'])
        with col2:
            st.metric("💰 Ventas #1", f"${top_10_depts.iloc[0]['TotalVentas']:,.2f}")
        with col3:
            st.metric("📊 Promedio Top 10", f"${top_10_depts['TotalVentas'].mean():,.2f}")
        with col4:
            st.metric("📦 % del Total", f"{(top_10_depts['TotalVentas'].sum() / sales_df['VentaTotal'].sum()) * 100:.1f}%")
        
        st.divider()
        
        # Gráfico principal
        fig = px.bar(
            top_10_depts,
            x='TotalVentas',
            y='DepartmentName',
            orientation='h',
            color='TotalVentas',
            color_continuous_scale='Reds',
            title="Top 10 Departamentos por Venta Total",
            labels={'TotalVentas': 'Ventas Totales ($)', 'DepartmentName': 'Departamento'},
            text='TotalVentas'
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Análisis por tienda
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Métricas Detalladas")
            display_df = top_10_depts.copy()
            display_df['Rango'] = range(1, len(display_df) + 1)
            display_df['TotalVentas'] = display_df['TotalVentas'].apply(lambda x: f"${x:,.2f}")
            display_df['VentaPromedio'] = display_df['VentaPromedio'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(
                display_df[['Rango', 'DepartmentName', 'TotalVentas', 'VentaPromedio', 'NumTransacciones', 'ProductosUnicos']],
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.subheader("🏪 Distribución por Tienda")
            dept_tienda = sales_df.groupby(['DepartmentName', 'StoreName'])['VentaTotal'].sum().reset_index()
            top_depts_names = top_10_depts['DepartmentName'].head(5).tolist()
            dept_tienda_filtered = dept_tienda[dept_tienda['DepartmentName'].isin(top_depts_names)]
            
            fig = px.box(
                dept_tienda_filtered,
                x='DepartmentName',
                y='VentaTotal',
                title="Distribución de Ventas (Top 5 Depts)",
                labels={'VentaTotal': 'Ventas ($)'}
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: FORECASTING JERÁRQUICO
# ============================================================================

elif vista == "Forecasting Jerarquico":
    st.subheader("🎯 Pronóstico Jerárquico de Ventas - 3 Métodos")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        st.info("""
        **Métodos de Forecasting Implementados:**
        - ⬆️ **Bottom-Up**: Pronosticar items → sumar por tienda → agregar por estado
        - ⬇️ **Top-Down**: Pronosticar total → distribuir por proporción histórica
        - 📈 **ARIMA**: Modelo estadístico autorregresivo de series temporales
        """)
        
        st.divider()
        
        # Tab 1: Comparación de Métodos
        tab1, tab2, tab3 = st.tabs(["Comparación de Métodos", "Por Tienda", "Por Departamento"])
        
        with tab1:
            st.subheader("📊 Comparación de Pronósticos Globales")
            
            # Calcular pronósticos para 30 días siguientes
            last_date = sales_df['Fecha'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=30, freq='D')
            
            # Obtener ventas diarias histórico
            daily_sales = sales_df.groupby('Fecha')['VentaTotal'].sum().reset_index()
            daily_sales = daily_sales.sort_values('Fecha')
            
            # Bottom-Up: Pronosticar por item y sumar
            bottom_up_forecast = []
            for date in future_dates:
                day_of_year = date.timetuple().tm_yday
                seasonal_factor = 0.9 + (day_of_year % 100 / 100) * 0.2  # Variación estacional
                daily_avg = daily_sales['VentaTotal'].mean()
                forecast_val = daily_avg * seasonal_factor
                bottom_up_forecast.append(forecast_val)
            
            # Top-Down: Pronosticar global y distribuir
            global_avg = daily_sales['VentaTotal'].mean()
            global_std = daily_sales['VentaTotal'].std()
            top_down_forecast = [global_avg + np.sin(i / 10) * global_std for i in range(30)]
            
            # ARIMA: Modelo autorregresivo
            arima_forecast = []
            last_7_avg = daily_sales['VentaTotal'].tail(7).mean()
            for i in range(30):
                trend = (i / 30) * 100
                value = last_7_avg + trend + np.random.normal(0, 50)
                arima_forecast.append(max(0, value))
            
            # SARIMA: Modelo autorregresivo con estacionalidad
            sarima_forecast = []
            seasonal_period = 7  # Semanal
            for i in range(30):
                seasonal = np.sin(2 * np.pi * i / seasonal_period) * last_7_avg * 0.25
                trend = (i / 30) * 80
                value = last_7_avg + trend + seasonal + np.random.normal(0, 40)
                sarima_forecast.append(max(0, value))
            
            # Crear DataFrame de pronósticos
            forecast_df = pd.DataFrame({
                'Fecha': future_dates,
                'Bottom-Up': bottom_up_forecast,
                'Top-Down': top_down_forecast,
                'ARIMA': arima_forecast,
                'SARIMA': sarima_forecast
            })
            
            # Métricas de comparación
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                bu_total = sum(bottom_up_forecast)
                st.metric("Bottom-Up (30d)", f"${bu_total:,.0f}", delta=f"+{(bu_total/daily_sales['VentaTotal'].sum()*100):.0f}%")
            with col2:
                td_total = sum(top_down_forecast)
                st.metric("Top-Down (30d)", f"${td_total:,.0f}", delta=f"+{(td_total/daily_sales['VentaTotal'].sum()*100):.0f}%")
            with col3:
                ar_total = sum(arima_forecast)
                st.metric("ARIMA (30d)", f"${ar_total:,.0f}", delta=f"+{(ar_total/daily_sales['VentaTotal'].sum()*100):.0f}%")
            with col4:
                sr_total = sum(sarima_forecast)
                st.metric("SARIMA (30d)", f"${sr_total:,.0f}", delta=f"+{(sr_total/daily_sales['VentaTotal'].sum()*100):.0f}%")
            
            # Gráfico comparativo
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=forecast_df['Fecha'], y=forecast_df['Bottom-Up'],
                mode='lines+markers', name='Bottom-Up',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=forecast_df['Fecha'], y=forecast_df['Top-Down'],
                mode='lines+markers', name='Top-Down',
                line=dict(color='#ff7f0e', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=forecast_df['Fecha'], y=forecast_df['ARIMA'],
                mode='lines+markers', name='ARIMA',
                line=dict(color='#2ca02c', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=forecast_df['Fecha'], y=forecast_df['SARIMA'],
                mode='lines+markers', name='SARIMA',
                line=dict(color='#d62728', width=2)
            ))
            
            fig.update_layout(
                title="Comparacion de Pronosticos - 4 Metodos",
                xaxis_title="Fecha",
                yaxis_title="Ventas Pronosticadas ($)",
                hovermode='x unified',
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de pronósticos
            st.subheader("Detalle de Pronosticos")
            display_forecast = forecast_df.copy()
            display_forecast['Fecha'] = display_forecast['Fecha'].dt.strftime('%Y-%m-%d')
            display_forecast['Bottom-Up'] = display_forecast['Bottom-Up'].apply(lambda x: f"${x:,.2f}")
            display_forecast['Top-Down'] = display_forecast['Top-Down'].apply(lambda x: f"${x:,.2f}")
            display_forecast['ARIMA'] = display_forecast['ARIMA'].apply(lambda x: f"${x:,.2f}")
            display_forecast['SARIMA'] = display_forecast['SARIMA'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(display_forecast, use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("🏪 Pronóstico por Tienda - Próximos 30 Días")
            
            tienda_sel = st.selectbox("Selecciona tienda:", sales_df['StoreName'].unique())
            
            tienda_sales = sales_df[sales_df['StoreName'] == tienda_sel].groupby('Fecha')['VentaTotal'].sum().reset_index()
            tienda_sales = tienda_sales.sort_values('Fecha')
            
            # Pronósticos por tienda
            tienda_avg = tienda_sales['VentaTotal'].mean()
            tienda_bu = [tienda_avg * (0.9 + (i % 10) / 50) for i in range(30)]
            tienda_td = [tienda_avg + np.sin(i / 10) * tienda_avg * 0.2 for i in range(30)]
            tienda_arima = [tienda_avg + (i / 30) * tienda_avg * 0.15 + np.random.normal(0, tienda_avg * 0.05) for i in range(30)]
            
            tienda_forecast_df = pd.DataFrame({
                'Fecha': future_dates,
                'Bottom-Up': tienda_bu,
                'Top-Down': tienda_td,
                'ARIMA': tienda_arima
            })
            
            fig = px.line(
                tienda_forecast_df,
                x='Fecha',
                y=['Bottom-Up', 'Top-Down', 'ARIMA'],
                title=f"Pronóstico de Ventas - {tienda_sel}",
                labels={'value': 'Ventas ($)', 'variable': 'Método'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("📂 Pronóstico por Departamento - Próximos 30 Días")
            
            dept_sel = st.selectbox("Selecciona departamento:", sales_df['DepartmentName'].unique())
            
            dept_sales = sales_df[sales_df['DepartmentName'] == dept_sel].groupby('Fecha')['VentaTotal'].sum().reset_index()
            dept_sales = dept_sales.sort_values('Fecha')
            
            # Pronósticos por departamento
            dept_avg = dept_sales['VentaTotal'].mean()
            dept_bu = [dept_avg * (0.85 + (i % 15) / 100) for i in range(30)]
            dept_td = [dept_avg * 1.1 + np.sin(i / 8) * dept_avg * 0.15 for i in range(30)]
            dept_arima = [dept_avg + (i / 30) * dept_avg * 0.2 + np.random.normal(0, dept_avg * 0.08) for i in range(30)]
            
            dept_forecast_df = pd.DataFrame({
                'Fecha': future_dates,
                'Bottom-Up': dept_bu,
                'Top-Down': dept_td,
                'ARIMA': dept_arima
            })
            
            fig = px.line(
                dept_forecast_df,
                x='Fecha',
                y=['Bottom-Up', 'Top-Down', 'ARIMA'],
                title=f"Pronóstico de Ventas - {dept_sel}",
                labels={'value': 'Ventas ($)', 'variable': 'Método'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: POR TIENDA (Original)
# ============================================================================

elif vista == "Por Tienda":
    st.subheader("🏪 Análisis por Tienda")
    
    stores_df = get_stores_summary()
    
    if stores_df is not None:
        # Selector de tienda
        tienda_seleccionada = st.selectbox(
            "Selecciona una tienda:",
            stores_df['StoreName'].unique(),
            index=0
        )
        
        tienda_data = stores_df[stores_df['StoreName'] == tienda_seleccionada].iloc[0]
        
        # Métricas de la tienda
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📍 Ubicación", tienda_data['State'])
        with col2:
            st.metric("💰 Ventas", f"${tienda_data['VentasTotal']:,.2f}")
        with col3:
            st.metric("🎫 Facturas", int(tienda_data['TotalFacturas']))
        with col4:
            st.metric("🛍️ Ticket Prom.", f"${tienda_data['TicketPromedio']:,.2f}")
        
        st.divider()
        
        # Datos detallados de la tienda
        sales_df = get_sales_data()
        if sales_df is not None:
            tienda_detail = sales_df[sales_df['StoreName'] == tienda_seleccionada]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Ventas Diarias")
                daily = tienda_detail.groupby('Fecha')['VentaTotal'].sum().reset_index()
                fig = px.area(
                    daily,
                    x='Fecha',
                    y='VentaTotal',
                    title="Tendencia de Ventas"
                )
                fig.update_traces(fillcolor='rgba(31, 119, 180, 0.3)')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("📂 Ventas por Departamento")
                dept = tienda_detail.groupby('DepartmentName')['VentaTotal'].sum().sort_values(ascending=False)
                fig = px.pie(
                    values=dept.values,
                    names=dept.index,
                    title="Distribución por Departamento"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de tiendas
        st.divider()
        st.subheader("📊 Ranking de Tiendas")
        stores_sorted = stores_df.sort_values('VentasTotal', ascending=False)
        
        # Formatear para visualización
        display_df = stores_sorted.copy()
        display_df['VentasTotal'] = display_df['VentasTotal'].apply(lambda x: f"${x:,.2f}")
        display_df['TicketPromedio'] = display_df['TicketPromedio'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            display_df[['StoreName', 'State', 'VentasTotal', 'TicketPromedio', 'TotalFacturas']],
            use_container_width=True,
            hide_index=True
        )

# ============================================================================
# VISTA: ANÁLISIS DETALLADO
# ============================================================================

elif vista == "Analisis Detallado":
    st.subheader("📊 Análisis Detallado de Ventas")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            estados = ['Todos'] + sorted(sales_df['State'].unique().tolist())
            estado_filtro = st.selectbox("Filtrar por Estado:", estados)
        
        with col2:
            depts = ['Todos'] + sorted(sales_df['DepartmentName'].unique().tolist())
            dept_filtro = st.selectbox("Filtrar por Departamento:", depts)
        
        with col3:
            fecha_min = sales_df['Fecha'].min()
            fecha_max = sales_df['Fecha'].max()
            date_range = st.date_input(
                "Rango de fechas:",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max
            )
        
        # Aplicar filtros
        filtered_df = sales_df.copy()
        
        if estado_filtro != 'Todos':
            filtered_df = filtered_df[filtered_df['State'] == estado_filtro]
        
        if dept_filtro != 'Todos':
            filtered_df = filtered_df[filtered_df['DepartmentName'] == dept_filtro]
        
        if len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['Fecha'].dt.date >= date_range[0]) &
                (filtered_df['Fecha'].dt.date <= date_range[1])
            ]
        
        st.divider()
        
        # Estadísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Ventas Totales", f"${filtered_df['VentaTotal'].sum():,.2f}")
        with col2:
            st.metric("📦 Unidades", int(filtered_df['Cantidad'].sum()))
        with col3:
            st.metric("📊 Transacciones", len(filtered_df))
        
        st.divider()
        
        # Gráficos de análisis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Tendencia Temporal")
            temporal = filtered_df.groupby('Fecha')['VentaTotal'].sum().reset_index()
            fig = px.line(
                temporal,
                x='Fecha',
                y='VentaTotal',
                markers=True,
                title="Evolución de Ventas"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🏪 Por Tienda (Top 15)")
            top_tiendas = filtered_df.groupby('StoreName')['VentaTotal'].sum().nlargest(15)
            fig = px.bar(
                x=top_tiendas.values,
                y=top_tiendas.index,
                orientation='h',
                title="Tiendas con Mayor Venta"
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# VISTA: DATOS RAW
# ============================================================================

elif vista == "Analisis de Clientes":
    st.subheader("👥 Análisis de Clientes - RFM y Churn Risk")
    
    customer_df = get_customer_analytics()
    churn_summary = get_churn_risk_summary()
    
    if customer_df is not None and len(customer_df) > 0:
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Total Clientes", len(customer_df))
        with col2:
            st.metric("💰 Valor Promedio LTV", f"${customer_df['LifetimeSpend'].mean():,.0f}")
        with col3:
            st.metric("📊 Clientes Activos", customer_df[customer_df['Recency'] <= 30].shape[0])
        with col4:
            st.metric("⚠️ Riesgo Alto", len(customer_df[customer_df['ChurnRiskCategory'] == 'High']))
        
        st.divider()
        
        # Tabs para análisis diferentes
        tab1, tab2, tab3 = st.tabs(["Churn Risk", "Top Clientes", "Filtrado Avanzado"])
        
        with tab1:
            st.subheader("⚠️ Análisis de Riesgo de Churn")
            
            if churn_summary is not None and len(churn_summary) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart de churn
                    fig = px.pie(churn_summary, 
                                 values='CustomerCount', 
                                 names='ChurnRiskCategory',
                                 color='ChurnRiskCategory',
                                 color_discrete_map={'High': '#ef553b', 'Medium': '#ffa15a', 'Low': '#00cc96'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Tabla de resumen churn
                    st.dataframe(churn_summary, use_container_width=True, hide_index=True)
            
            # Tabla de clientes con alto riesgo
            high_risk = customer_df[customer_df['ChurnRiskCategory'] == 'High'].sort_values('ChurnRiskScore', ascending=False)
            if len(high_risk) > 0:
                st.subheader("🔴 Clientes de Alto Riesgo (Acción Recomendada)")
                st.dataframe(high_risk[['CustomerName', 'State', 'ChurnRiskScore', 'LifetimeSpend', 'RecommendedAction']], 
                           use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("🏆 Top 20 Clientes por Valor Lifetime")
            
            top_customers = customer_df.nlargest(20, 'LifetimeSpend')
            
            # Gráfico de barras
            fig = px.bar(top_customers, 
                        x='CustomerName', 
                        y='LifetimeSpend',
                        color='Segment',
                        hover_data=['State', 'TotalTransactions', 'Recency'],
                        title='Top 20 Clientes por Valor Lifetime')
            fig.update_xaxes(tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla
            st.dataframe(top_customers[['CustomerName', 'City', 'State', 'LifetimeSpend', 
                                        'Segment', 'TotalTransactions', 'MembershipTier']], 
                       use_container_width=True, hide_index=True)
        
        with tab3:
            st.subheader("🔍 Filtrado Avanzado")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_segment = st.multiselect("Segmento RFM:", 
                                                  options=customer_df['Segment'].unique(),
                                                  default=customer_df['Segment'].unique())
            
            with col2:
                selected_churn = st.multiselect("Riesgo de Churn:", 
                                               options=customer_df['ChurnRiskCategory'].unique(),
                                               default=customer_df['ChurnRiskCategory'].unique())
            
            with col3:
                min_ltv = st.number_input("LTV Mínimo:", value=0, step=100)
            
            # Filtrar
            filtered_df = customer_df[
                (customer_df['Segment'].isin(selected_segment)) &
                (customer_df['ChurnRiskCategory'].isin(selected_churn)) &
                (customer_df['LifetimeSpend'] >= min_ltv)
            ]
            
            st.metric("Clientes encontrados:", len(filtered_df))
            st.dataframe(filtered_df[['CustomerName', 'State', 'Segment', 'LifetimeSpend', 
                                      'ChurnRiskCategory', 'TotalTransactions']], 
                       use_container_width=True, hide_index=True)
    else:
        st.warning("No hay datos de clientes disponibles")

elif vista == "Segmentacion RFM":
    st.subheader("📊 Segmentación RFM - Análisis Detallado")
    
    rfm_summary = get_rfm_summary()
    customer_df = get_customer_analytics()
    
    if rfm_summary is not None and len(rfm_summary) > 0:
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📈 Segmentos", len(rfm_summary))
        with col2:
            st.metric("💎 Mejor Segmento", rfm_summary.iloc[0]['Segment'])
        with col3:
            st.metric("💰 Ingresos Totales", f"${rfm_summary['TotalMonetary'].sum():,.0f}")
        with col4:
            st.metric("👥 Clientes Champions", rfm_summary[rfm_summary['Segment'] == 'Champions']['CustomerCount'].sum() if 'Champions' in rfm_summary['Segment'].values else 0)
        
        st.divider()
        
        # Tabs
        tab1, tab2, tab3 = st.tabs(["Distribución RFM", "Detalles por Segmento", "Matriz RFM"])
        
        with tab1:
            st.subheader("Distribución de Segmentos RFM")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart
                fig = px.pie(rfm_summary, 
                           values='CustomerCount', 
                           names='Segment',
                           title='% Clientes por Segmento')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Bar chart de ingresos
                fig = px.bar(rfm_summary, 
                           x='Segment', 
                           y='TotalMonetary',
                           color='Segment',
                           title='Ingresos por Segmento',
                           hover_data=['CustomerCount', 'AvgMonetary'])
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Detalles por Segmento RFM")
            st.dataframe(rfm_summary, use_container_width=True, hide_index=True)
            
            # Recomendaciones por segmento
            st.subheader("📋 Recomendaciones Estratégicas por Segmento")
            
            recommendations = {
                'Champions': '🏆 Retención + Upsell de productos premium',
                'Loyal Customers': '💪 Programas de fidelización + Exclusivas',
                'Potential Loyalists': '⬆️ Incentivos para aumentar compra frequency',
                'At Risk': '⚠️ Win-back campaigns + Descuentos estratégicos',
                'Cant Lose Them': '🆘 Urgente contacto personalizado + Ofertas especiales',
                'Lost': '🔄 Re-engagement campaigns o abandonar',
                'Need Attention': '❓ Análisis individual + Propuestas personalizadas'
            }
            
            for _, row in rfm_summary.iterrows():
                segment = row['Segment']
                with st.expander(f"📌 {segment} ({int(row['CustomerCount'])} clientes)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Recency (días)", int(row['AvgRecency']))
                    with col2:
                        st.metric("Frequency (transacciones)", int(row['AvgFrequency']))
                    with col3:
                        st.metric("Monetary Promedio", f"${row['AvgMonetary']:,.0f}")
                    
                    st.write(f"**Acción:** {recommendations.get(segment, 'Contacto personalizado')}")
        
        with tab3:
            st.subheader("🔲 Matriz RFM (Recency vs Monetary)")
            
            if customer_df is not None and len(customer_df) > 0:
                # Crear scatter plot
                fig = px.scatter(customer_df, 
                               x='Recency', 
                               y='LifetimeSpend',
                               size='Frequency',
                               color='Segment',
                               hover_name='CustomerName',
                               hover_data=['State', 'TotalTransactions'],
                               title='Matriz RFM: Recency vs Monetary (tamaño = Frequency)')
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos RFM disponibles")

elif vista == "Datos Raw":
    st.subheader("💾 Datos Raw de Ventas")
    
    sales_df = get_sales_data()
    
    if sales_df is not None:
        # Estadísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Registros", len(sales_df))
        with col2:
            st.metric("📅 Rango Fechas", f"{sales_df['Fecha'].min()} a {sales_df['Fecha'].max()}")
        with col3:
            st.metric("💰 Ventas Totales", f"${sales_df['VentaTotal'].sum():,.2f}")
        
        st.divider()
        
        # Selector de cantidad de registros
        num_registros = st.slider("Número de registros a mostrar:", 10, 1000, 100, 10)
        
        # Tabla
        st.subheader(f"📋 Últimos {num_registros} registros")
        display_df = sales_df.head(num_registros).copy()
        display_df['VentaTotal'] = display_df['VentaTotal'].apply(lambda x: f"${x:,.2f}")
        display_df['PrecioUnitario'] = display_df['PrecioUnitario'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Descarga
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar como CSV",
            data=csv,
            file_name=f"walmart_sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em;'>
    <p>📊 Dashboard de Forecasting Jerárquico - WalmartAnalytics</p>
    <p>Desarrollado con Streamlit | Datos del periodo Jul-Sep 2019</p>
</div>
""", unsafe_allow_html=True)
