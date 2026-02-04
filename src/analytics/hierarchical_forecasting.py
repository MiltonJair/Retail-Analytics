"""
HIERARCHICAL FORECASTING - WALMART ANALYTICS
==============================================
Script para realizar pronósticos jerárquicos de ventas usando datos de Walmart.

Jerarquías implementadas:
1. Geográfica: Total → Región → Estado → Ciudad → Tienda
2. Producto: Total → Departamento → Item

Métodos:
- Bottom-Up: Pronosticar a nivel más bajo y agregar
- Top-Down: Pronosticar total y distribuir
- Reconciliación óptima: MinTrace, OLS

Autor: Analytics Team
Fecha: 2026-02-03
"""

import pyodbc
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Para forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    print("⚠️ Prophet no instalado. Instalar con: pip install prophet")
    PROPHET_AVAILABLE = False

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.arima.model import ARIMA
    STATSMODELS_AVAILABLE = True
except ImportError:
    print("⚠️ Statsmodels no instalado. Instalar con: pip install statsmodels")
    STATSMODELS_AVAILABLE = False


class WalmartHierarchicalForecasting:
    """
    Clase principal para ejecutar Hierarchical Forecasting en datos de Walmart
    """
    
    def __init__(self, server='localhost', database='WalmartAnalytics'):
        """
        Inicializar conexión a base de datos
        
        Args:
            server: Nombre del servidor SQL
            database: Nombre de la base de datos
        """
        self.server = server
        self.database = database
        self.conn = None
        self.df_raw = None
        self.df_hierarchy = None
        self.forecasts = {}
        
    def connect_database(self):
        """Conectar a SQL Server con múltiples drivers"""
        # Lista de drivers a probar en orden de preferencia
        drivers = [
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 13 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server"
        ]
        
        for driver in drivers:
            try:
                conn_string = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={self.server};"
                    f"DATABASE={self.database};"
                    "Trusted_Connection=yes;"
                    "TrustServerCertificate=yes;"
                )
                self.conn = pyodbc.connect(conn_string, timeout=5)
                print(f"✅ Conectado a {self.database} usando: {driver}")
                return True
            except Exception as e:
                continue
        
        # Si ningún driver funcionó
        print(f"❌ No se pudo conectar a SQL Server")
        print("\n💡 Soluciones:")
        print("   1. Verificar que SQL Server esté corriendo")
        print("      - Abrir 'SQL Server Configuration Manager'")
        print("      - Verificar servicio 'SQL Server (MSSQLSERVER)'")
        print("   2. Instalar ODBC Driver 17: https://aka.ms/downloadmsodbcsql")
        print("   3. Ajustar servidor: cambiar 'localhost' por '(localdb)\\MSSQLLocalDB'")
        
        return False
    
    def extract_sales_data(self):
        """
        Extraer datos históricos de ventas con estructura jerárquica
        """
        query = """
        SELECT 
            CAST(ih.InvoiceDate AS DATE) as Fecha,
            DATEPART(YEAR, ih.InvoiceDate) as Año,
            DATEPART(MONTH, ih.InvoiceDate) as Mes,
            DATEPART(DAY, ih.InvoiceDate) as Dia,
            DATENAME(WEEKDAY, ih.InvoiceDate) as DiaSemana,
            
            -- Jerarquía Geográfica
            s.State,
            s.City,
            s.StoreID,
            s.StoreName,
            
            -- Jerarquía Producto
            d.DepartmentID,
            d.DepartmentName,
            i.ItemID,
            i.ItemName,
            
            -- Métricas
            id.QuantitySold as Cantidad,
            id.LineTotal as VentaTotal,
            id.UnitPrice as PrecioUnitario
            
        FROM InvoiceHeaders ih
        INNER JOIN InvoiceDetails id ON ih.InvoiceID = id.InvoiceID
        INNER JOIN Stores s ON ih.StoreID = s.StoreID
        INNER JOIN Items i ON id.ItemID = i.ItemID
        INNER JOIN Departments d ON i.DepartmentID = d.DepartmentID
        
        ORDER BY ih.InvoiceDate, s.State, d.DepartmentName;
        """
        
        if self.conn is None:
            print("❌ No hay conexión a la base de datos")
            return False
        
        try:
            self.df_raw = pd.read_sql(query, self.conn)
            self.df_raw['Fecha'] = pd.to_datetime(self.df_raw['Fecha'])
            
            print(f"✅ Datos extraídos: {len(self.df_raw):,} registros")
            print(f"   📅 Rango: {self.df_raw['Fecha'].min()} a {self.df_raw['Fecha'].max()}")
            print(f"   🏪 Tiendas: {self.df_raw['StoreID'].nunique()}")
            print(f"   📦 Departamentos: {self.df_raw['DepartmentID'].nunique()}")
            print(f"   🛍️  Items: {self.df_raw['ItemID'].nunique()}")
            return True
            
        except Exception as e:
            print(f"❌ Error extrayendo datos: {e}")
            return False
    
    def create_hierarchical_structure(self):
        """
        Crear estructura de datos jerárquica agregada por nivel
        """
        if self.df_raw is None:
            print("❌ Primero debes extraer datos con extract_sales_data()")
            return False
        
        print("\n🏗️ Construyendo estructura jerárquica...")
        
        # Agregación diaria por diferentes niveles
        hierarchies = {}
        
        # Nivel 0: Total Nacional
        hierarchies['total'] = self.df_raw.groupby('Fecha').agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['total']['Nivel'] = 'Total'
        hierarchies['total']['Clave'] = 'TOTAL'
        
        # Nivel 1: Por Estado
        hierarchies['state'] = self.df_raw.groupby(['Fecha', 'State']).agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['state']['Nivel'] = 'State'
        hierarchies['state']['Clave'] = hierarchies['state']['State']
        
        # Nivel 2: Por Ciudad
        hierarchies['city'] = self.df_raw.groupby(['Fecha', 'State', 'City']).agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['city']['Nivel'] = 'City'
        hierarchies['city']['Clave'] = hierarchies['city']['City']
        
        # Nivel 3: Por Tienda
        hierarchies['store'] = self.df_raw.groupby(['Fecha', 'State', 'City', 'StoreID', 'StoreName']).agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['store']['Nivel'] = 'Store'
        hierarchies['store']['Clave'] = hierarchies['store']['StoreName']
        
        # Jerarquía de Productos
        hierarchies['department'] = self.df_raw.groupby(['Fecha', 'DepartmentName']).agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['department']['Nivel'] = 'Department'
        hierarchies['department']['Clave'] = hierarchies['department']['DepartmentName']
        
        # Nivel detalle: Por Item
        hierarchies['item'] = self.df_raw.groupby(['Fecha', 'DepartmentName', 'ItemName']).agg({
            'VentaTotal': 'sum',
            'Cantidad': 'sum'
        }).reset_index()
        hierarchies['item']['Nivel'] = 'Item'
        hierarchies['item']['Clave'] = hierarchies['item']['ItemName']
        
        self.hierarchies = hierarchies
        
        # Resumen
        print("\n📊 Estructura creada:")
        for level, df in hierarchies.items():
            unique_keys = df['Clave'].nunique()
            date_range = len(df['Fecha'].unique())
            print(f"   • {level.upper():<12}: {len(df):>5} registros | {unique_keys} entidades | {date_range} días")
        
        return True
    
    def forecast_simple_exponential(self, series, periods=7):
        """
        Pronóstico simple usando Exponential Smoothing
        
        Args:
            series: Serie temporal de pandas
            periods: Número de períodos a pronosticar
            
        Returns:
            DataFrame con forecast
        """
        if not STATSMODELS_AVAILABLE or len(series) < 7:
            # Fallback: usar media móvil simple
            mean_value = series.tail(7).mean()
            return pd.Series([mean_value] * periods)
        
        try:
            model = ExponentialSmoothing(
                series, 
                seasonal_periods=7,
                trend='add', 
                seasonal='add'
            )
            fitted_model = model.fit()
            forecast = fitted_model.forecast(periods)
            return forecast
        except:
            # Si falla, usar media de últimos 7 días
            mean_value = series.tail(7).mean()
            return pd.Series([mean_value] * periods)
    
    def forecast_arima(self, series, periods=7):
        """
        Pronóstico usando modelo ARIMA
        
        Args:
            series: Serie temporal de pandas
            periods: Número de períodos a pronosticar
            
        Returns:
            Series con forecast
        """
        if not STATSMODELS_AVAILABLE or len(series) < 7:
            # Fallback: usar media móvil simple
            mean_value = series.tail(7).mean()
            return pd.Series([mean_value] * periods)
        
        try:
            # Auto ARIMA simplificado - usar orden común (1,1,1)
            model = ARIMA(series, order=(1, 1, 1))
            fitted_model = model.fit()
            forecast = fitted_model.forecast(steps=periods)
            return forecast
        except:
            # Si ARIMA falla, usar media de últimos 7 días
            mean_value = series.tail(7).mean()
            return pd.Series([mean_value] * periods)
    
    def forecast_prophet(self, df, date_col='Fecha', value_col='VentaTotal', periods=7):
        """
        Pronóstico usando Facebook Prophet
        
        Args:
            df: DataFrame con datos históricos
            date_col: Nombre columna de fecha
            value_col: Nombre columna de valor a pronosticar
            periods: Días a pronosticar
            
        Returns:
            DataFrame con forecast
        """
        if not PROPHET_AVAILABLE or len(df) < 7:
            return None
        
        try:
            # Preparar datos para Prophet
            prophet_df = df[[date_col, value_col]].copy()
            prophet_df.columns = ['ds', 'y']
            
            # Crear y entrenar modelo
            model = Prophet(
                daily_seasonality=True,
                yearly_seasonality=False,
                weekly_seasonality=True
            )
            model.fit(prophet_df)
            
            # Hacer pronóstico
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future)
            
            return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
            
        except Exception as e:
            print(f"   ⚠️ Prophet falló: {e}")
            return None
    
    def run_bottom_up_forecast(self, level='store', periods=7):
        """
        Método Bottom-Up: Pronosticar nivel más bajo y agregar
        
        Args:
            level: Nivel jerárquico base ('store', 'item')
            periods: Días a pronosticar
        """
        print(f"\n🔽 Bottom-Up Forecast - Nivel: {level.upper()}")
        
        if level not in self.hierarchies:
            print(f"❌ Nivel '{level}' no encontrado")
            return None
        
        df = self.hierarchies[level].copy()
        unique_keys = df['Clave'].unique()
        
        forecasts_list = []
        
        for key in unique_keys:
            series_data = df[df['Clave'] == key].sort_values('Fecha')
            
            if len(series_data) < 3:
                continue
            
            # Pronosticar
            series = series_data.set_index('Fecha')['VentaTotal']
            forecast = self.forecast_simple_exponential(series, periods)
            
            # Crear fechas futuras
            last_date = series_data['Fecha'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods)
            
            # Guardar forecast
            for date, value in zip(future_dates, forecast):
                forecasts_list.append({
                    'Fecha': date,
                    'Clave': key,
                    'Nivel': level,
                    'Forecast': value,
                    'Metodo': 'Bottom-Up'
                })
        
        forecast_df = pd.DataFrame(forecasts_list)
        
        # Agregar al total
        total_forecast = forecast_df.groupby('Fecha').agg({
            'Forecast': 'sum'
        }).reset_index()
        
        print(f"   ✅ Forecast generado para {len(unique_keys)} entidades")
        print(f"   📈 Total proyectado (7 días): ${total_forecast['Forecast'].sum():,.2f}")
        
        self.forecasts['bottom_up'] = {
            'detail': forecast_df,
            'total': total_forecast
        }
        
        return forecast_df
    
    def run_top_down_forecast(self, periods=7):
        """
        Método Top-Down: Pronosticar total y distribuir proporcionalmente
        
        Args:
            periods: Días a pronosticar
        """
        print(f"\n🔼 Top-Down Forecast")
        
        # Pronosticar total nacional
        total_data = self.hierarchies['total'].copy()
        series = total_data.set_index('Fecha')['VentaTotal']
        
        forecast_total = self.forecast_simple_exponential(series, periods)
        
        # Crear fechas futuras
        last_date = total_data['Fecha'].max()
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods)
        
        # Calcular proporciones históricas (últimos 30 días)
        recent_data = self.df_raw[self.df_raw['Fecha'] >= (last_date - timedelta(days=30))]
        
        # Proporciones por tienda
        store_props = recent_data.groupby('StoreName')['VentaTotal'].sum()
        store_props = store_props / store_props.sum()
        
        # Distribuir forecast
        forecasts_list = []
        for date, total_value in zip(future_dates, forecast_total):
            for store, prop in store_props.items():
                forecasts_list.append({
                    'Fecha': date,
                    'Clave': store,
                    'Nivel': 'store',
                    'Forecast': total_value * prop,
                    'Metodo': 'Top-Down'
                })
        
        forecast_df = pd.DataFrame(forecasts_list)
        
        total_forecast = pd.DataFrame({
            'Fecha': future_dates,
            'Forecast': forecast_total
        })
        
        print(f"   ✅ Total proyectado (7 días): ${forecast_total.sum():,.2f}")
        print(f"   📊 Distribuido a {len(store_props)} tiendas")
        
        self.forecasts['top_down'] = {
            'detail': forecast_df,
            'total': total_forecast
        }
        
        return forecast_df
    
    def run_arima_forecast(self, level='store', periods=7):
        """
        Método ARIMA: Pronosticar usando modelo ARIMA por nivel
        
        Args:
            level: Nivel jerárquico base ('store', 'item')
            periods: Días a pronosticar
        """
        print(f"\n📈 ARIMA Forecast - Nivel: {level.upper()}")
        
        if level not in self.hierarchies:
            print(f"❌ Nivel '{level}' no encontrado")
            return None
        
        df = self.hierarchies[level].copy()
        unique_keys = df['Clave'].unique()
        
        forecasts_list = []
        
        for key in unique_keys:
            series_data = df[df['Clave'] == key].sort_values('Fecha')
            
            if len(series_data) < 3:
                continue
            
            # Pronosticar con ARIMA
            series = series_data.set_index('Fecha')['VentaTotal']
            forecast = self.forecast_arima(series, periods)
            
            # Crear fechas futuras
            last_date = series_data['Fecha'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods)
            
            # Guardar forecast
            for date, value in zip(future_dates, forecast):
                forecasts_list.append({
                    'Fecha': date,
                    'Clave': key,
                    'Nivel': level,
                    'Forecast': value,
                    'Metodo': 'ARIMA'
                })
        
        forecast_df = pd.DataFrame(forecasts_list)
        
        # Agregar al total
        total_forecast = forecast_df.groupby('Fecha').agg({
            'Forecast': 'sum'
        }).reset_index()
        
        print(f"   ✅ Forecast ARIMA generado para {len(unique_keys)} entidades")
        print(f"   📈 Total proyectado (7 días): ${total_forecast['Forecast'].sum():,.2f}")
        
        self.forecasts['arima'] = {
            'detail': forecast_df,
            'total': total_forecast
        }
        
        return forecast_df
    
    def visualize_forecasts(self, save_path='output'):
        """
        Crear visualizaciones de los pronósticos
        
        Args:
            save_path: Carpeta donde guardar gráficos
        """
        print(f"\n📊 Generando visualizaciones...")
        
        import os
        os.makedirs(save_path, exist_ok=True)
        
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Gráfico 1: Comparación Bottom-Up vs Top-Down (Total)
        if 'bottom_up' in self.forecasts and 'top_down' in self.forecasts:
            fig, ax = plt.subplots(figsize=(14, 6))
            
            # Datos históricos
            historical = self.hierarchies['total'].copy()
            ax.plot(historical['Fecha'], historical['VentaTotal'], 
                   label='Histórico', linewidth=2, color='#2E86AB')
            
            # Bottom-Up
            bu_total = self.forecasts['bottom_up']['total']
            ax.plot(bu_total['Fecha'], bu_total['Forecast'], 
                   label='Bottom-Up', linewidth=2, linestyle='--', 
                   marker='o', color='#06A77D')
            
            # Top-Down
            td_total = self.forecasts['top_down']['total']
            ax.plot(td_total['Fecha'], td_total['Forecast'], 
                   label='Top-Down', linewidth=2, linestyle='--', 
                   marker='s', color='#D62246')
            
            # ARIMA
            if 'arima' in self.forecasts:
                arima_total = self.forecasts['arima']['total']
                ax.plot(arima_total['Fecha'], arima_total['Forecast'], 
                       label='ARIMA', linewidth=2, linestyle=':', 
                       marker='^', color='#F77F00')
            
            ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
            ax.set_ylabel('Ventas Totales ($)', fontsize=12, fontweight='bold')
            ax.set_title('Hierarchical Forecasting - Walmart Ventas Totales', 
                        fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            filepath = os.path.join(save_path, 'forecast_total_comparison.png')
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"   ✅ Guardado: {filepath}")
            plt.close()
        
        # Gráfico 2: Forecast por Tienda (Bottom-Up)
        if 'bottom_up' in self.forecasts:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            bu_detail = self.forecasts['bottom_up']['detail']
            
            for store in bu_detail['Clave'].unique():
                store_data = bu_detail[bu_detail['Clave'] == store]
                ax.plot(store_data['Fecha'], store_data['Forecast'], 
                       label=store, marker='o', linewidth=2)
            
            ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
            ax.set_ylabel('Ventas Proyectadas ($)', fontsize=12, fontweight='bold')
            ax.set_title('Forecast por Tienda - Bottom-Up Method', 
                        fontsize=14, fontweight='bold')
            ax.legend(fontsize=9, loc='best')
            ax.grid(alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            filepath = os.path.join(save_path, 'forecast_por_tienda.png')
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"   ✅ Guardado: {filepath}")
            plt.close()
        
        # Gráfico 3: Distribución de Forecast por Región
        if 'bottom_up' in self.forecasts:
            # Agregar estado a los forecasts
            bu_detail = self.forecasts['bottom_up']['detail']
            
            # Mapear tiendas a estados
            store_state_map = self.df_raw[['StoreName', 'State']].drop_duplicates()
            bu_detail_state = bu_detail.merge(
                store_state_map, 
                left_on='Clave', 
                right_on='StoreName', 
                how='left'
            )
            
            if 'State' in bu_detail_state.columns:
                state_forecast = bu_detail_state.groupby(['Fecha', 'State'])['Forecast'].sum().reset_index()
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                for state in state_forecast['State'].unique():
                    state_data = state_forecast[state_forecast['State'] == state]
                    ax.bar(state_data['Fecha'], state_data['Forecast'], 
                          label=state, alpha=0.8)
                
                ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
                ax.set_ylabel('Ventas Proyectadas ($)', fontsize=12, fontweight='bold')
                ax.set_title('Forecast por Estado - 7 Días', 
                            fontsize=14, fontweight='bold')
                ax.legend(fontsize=11)
                ax.grid(alpha=0.3, axis='y')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                filepath = os.path.join(save_path, 'forecast_por_region.png')
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
                print(f"   ✅ Guardado: {filepath}")
                plt.close()
        
        print(f"\n✅ Visualizaciones completas guardadas en: {save_path}/")
    
    def create_dashboard(self, save_path='output'):
        """
        Crear dashboard interactivo con todos los análisis
        
        Args:
            save_path: Carpeta donde guardar dashboard
        """
        print(f"\n📊 Creando Dashboard completo...")
        
        import os
        os.makedirs(save_path, exist_ok=True)
        
        # Crear figura con múltiples subplots
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Histórico + Forecast Total (Grande - ocupa 2 columnas)
        ax1 = fig.add_subplot(gs[0, :2])
        historical = self.hierarchies['total'].copy()
        ax1.plot(historical['Fecha'], historical['VentaTotal'], 
                label='Histórico', linewidth=3, color='#2E86AB', marker='o')
        
        if 'bottom_up' in self.forecasts:
            bu_total = self.forecasts['bottom_up']['total']
            ax1.plot(bu_total['Fecha'], bu_total['Forecast'], 
                   label='Forecast Bottom-Up', linewidth=2.5, linestyle='--', 
                   marker='o', color='#06A77D', markersize=8)
        
        if 'top_down' in self.forecasts:
            td_total = self.forecasts['top_down']['total']
            ax1.plot(td_total['Fecha'], td_total['Forecast'], 
                   label='Forecast Top-Down', linewidth=2.5, linestyle='--', 
                   marker='s', color='#D62246', markersize=8)
        
        if 'arima' in self.forecasts:
            arima_total = self.forecasts['arima']['total']
            ax1.plot(arima_total['Fecha'], arima_total['Forecast'], 
                   label='Forecast ARIMA', linewidth=2.5, linestyle=':', 
                   marker='^', color='#F77F00', markersize=8)
        
        ax1.set_title('Ventas Históricas y Pronósticos - Total Nacional', 
                     fontsize=14, fontweight='bold', pad=15)
        ax1.set_xlabel('Fecha', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Ventas ($)', fontsize=11, fontweight='bold')
        ax1.legend(fontsize=10, loc='best')
        ax1.grid(alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. Métricas Resumen
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.axis('off')
        
        # Calcular métricas
        total_hist = historical['VentaTotal'].sum()
        avg_hist = historical['VentaTotal'].mean()
        
        if 'bottom_up' in self.forecasts:
            total_forecast = self.forecasts['bottom_up']['total']['Forecast'].sum()
            avg_forecast = self.forecasts['bottom_up']['total']['Forecast'].mean()
            growth = ((avg_forecast - avg_hist) / avg_hist) * 100
        else:
            total_forecast = 0
            avg_forecast = 0
            growth = 0
        
        metrics_text = f"""
        📊 MÉTRICAS CLAVE
        ═══════════════════
        
        Histórico:
        • Total: ${total_hist:,.0f}
        • Promedio: ${avg_hist:,.0f}/día
        
        Forecast (7 días):
        • Total: ${total_forecast:,.0f}
        • Promedio: ${avg_forecast:,.0f}/día
        
        Crecimiento:
        • {growth:+.1f}%
        """
        
        ax2.text(0.1, 0.5, metrics_text, fontsize=11, family='monospace',
                verticalalignment='center', bbox=dict(boxstyle='round', 
                facecolor='wheat', alpha=0.3))
        
        # 3. Forecast por Tienda
        ax3 = fig.add_subplot(gs[1, :])
        
        if 'bottom_up' in self.forecasts:
            bu_detail = self.forecasts['bottom_up']['detail']
            colors = plt.cm.Set3(range(len(bu_detail['Clave'].unique())))
            
            for idx, store in enumerate(bu_detail['Clave'].unique()):
                store_data = bu_detail[bu_detail['Clave'] == store]
                ax3.plot(store_data['Fecha'], store_data['Forecast'], 
                        label=store, marker='o', linewidth=2.5, 
                        color=colors[idx], markersize=7)
        
        ax3.set_title('Pronóstico por Tienda - Bottom-Up', 
                     fontsize=14, fontweight='bold', pad=15)
        ax3.set_xlabel('Fecha', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Ventas Proyectadas ($)', fontsize=11, fontweight='bold')
        ax3.legend(fontsize=9, loc='best', ncol=2)
        ax3.grid(alpha=0.3)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # 4. Distribución por Estado (Bar Chart)
        ax4 = fig.add_subplot(gs[2, 0])
        
        if 'bottom_up' in self.forecasts:
            bu_detail = self.forecasts['bottom_up']['detail']
            store_state_map = self.df_raw[['StoreName', 'State']].drop_duplicates()
            bu_detail_state = bu_detail.merge(store_state_map, 
                                              left_on='Clave', 
                                              right_on='StoreName', 
                                              how='left')
            
            if 'State' in bu_detail_state.columns:
                state_totals = bu_detail_state.groupby('State')['Forecast'].sum()
                colors_state = ['#06A77D', '#D62246', '#1f77b4', '#ff7f0e', '#2ca02c']
                ax4.bar(state_totals.index, state_totals.values, 
                       color=colors_state[:len(state_totals)], alpha=0.8)
                ax4.set_title('Total por Estado (7 días)', fontsize=12, fontweight='bold')
                ax4.set_ylabel('Ventas ($)', fontsize=10, fontweight='bold')
                ax4.tick_params(axis='x', rotation=45)
                ax4.grid(alpha=0.3, axis='y')
                
                # Añadir valores en las barras
                for i, v in enumerate(state_totals.values):
                    ax4.text(i, v, f'${v:,.0f}', ha='center', va='bottom', fontweight='bold', fontsize=8)
        
        # 5. Top 5 Tiendas
        ax5 = fig.add_subplot(gs[2, 1])
        
        if 'bottom_up' in self.forecasts:
            bu_detail = self.forecasts['bottom_up']['detail']
            top_stores = bu_detail.groupby('Clave')['Forecast'].sum().nlargest(5)
            
            ax5.barh(range(len(top_stores)), top_stores.values, color='#2E86AB', alpha=0.8)
            ax5.set_yticks(range(len(top_stores)))
            ax5.set_yticklabels([name[:25] + '...' if len(name) > 25 else name 
                                for name in top_stores.index], fontsize=9)
            ax5.set_title('Top 5 Tiendas - Forecast', fontsize=12, fontweight='bold')
            ax5.set_xlabel('Ventas Proyectadas ($)', fontsize=10, fontweight='bold')
            ax5.grid(alpha=0.3, axis='x')
            
            # Añadir valores
            for i, v in enumerate(top_stores.values):
                ax5.text(v, i, f' ${v:,.0f}', va='center', fontweight='bold')
        
        # 6. Tendencia Diaria
        ax6 = fig.add_subplot(gs[2, 2])
        
        if 'bottom_up' in self.forecasts:
            bu_total = self.forecasts['bottom_up']['total']
            ax6.plot(bu_total['Fecha'], bu_total['Forecast'], 
                    marker='o', linewidth=3, color='#06A77D', markersize=10)
            ax6.fill_between(bu_total['Fecha'], bu_total['Forecast'], 
                           alpha=0.3, color='#06A77D')
            ax6.set_title('Tendencia Diaria - Forecast', fontsize=12, fontweight='bold')
            ax6.set_xlabel('Fecha', fontsize=10, fontweight='bold')
            ax6.set_ylabel('Ventas ($)', fontsize=10, fontweight='bold')
            ax6.grid(alpha=0.3)
            plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45)
        
        # Título principal
        fig.suptitle('📊 WALMART HIERARCHICAL FORECASTING - DASHBOARD EJECUTIVO', 
                    fontsize=18, fontweight='bold', y=0.98)
        
        # Guardar
        filepath = os.path.join(save_path, 'dashboard_completo.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"   ✅ Dashboard guardado: {filepath}")
        
        # Mostrar en pantalla
        plt.show()
        plt.close()
    
    def export_results(self, save_path='output'):
        """
        Exportar resultados a CSV y Excel
        
        Args:
            save_path: Carpeta donde guardar archivos
        """
        print(f"\n💾 Exportando resultados...")
        
        import os
        os.makedirs(save_path, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Exportar cada forecast
        for method, data in self.forecasts.items():
            if 'detail' in data:
                filename = f'forecast_{method}_detail_{timestamp}.csv'
                filepath = os.path.join(save_path, filename)
                data['detail'].to_csv(filepath, index=False)
                print(f"   ✅ {filename}")
            
            if 'total' in data:
                filename = f'forecast_{method}_total_{timestamp}.csv'
                filepath = os.path.join(save_path, filename)
                data['total'].to_csv(filepath, index=False)
                print(f"   ✅ {filename}")
        
        # Crear resumen ejecutivo
        if self.forecasts:
            summary_data = []
            
            for method, data in self.forecasts.items():
                if 'total' in data:
                    total_forecast = data['total']['Forecast'].sum()
                    summary_data.append({
                        'Metodo': method,
                        'Total_7_Dias': total_forecast,
                        'Promedio_Diario': total_forecast / 7,
                        'Fecha_Generacion': timestamp
                    })
            
            summary_df = pd.DataFrame(summary_data)
            filename = f'forecast_summary_{timestamp}.csv'
            filepath = os.path.join(save_path, filename)
            summary_df.to_csv(filepath, index=False)
            print(f"   ✅ {filename}")
            
            # Mostrar resumen
            print("\n📋 RESUMEN EJECUTIVO:")
            print("="*60)
            for _, row in summary_df.iterrows():
                print(f"   {row['Metodo'].upper():<15}: ${row['Total_7_Dias']:>12,.2f} (7 días)")
                print(f"   {'Promedio/día':<15}: ${row['Promedio_Diario']:>12,.2f}")
                print("-"*60)
        
        print(f"\n✅ Todos los archivos guardados en: {save_path}/")
    
    def run_complete_analysis(self, forecast_periods=7):
        """
        Ejecutar análisis completo de Hierarchical Forecasting
        
        Args:
            forecast_periods: Días a pronosticar (default: 7)
        """
        print("="*70)
        print(" 🎯 WALMART HIERARCHICAL FORECASTING - ANÁLISIS COMPLETO")
        print("="*70)
        
        # Paso 1: Conectar
        if not self.connect_database():
            print("\n⚠️ No se pudo establecer conexión")
            return False
        
        # Paso 2: Extraer datos
        if not self.extract_sales_data():
            return False
        
        # Paso 3: Crear estructura jerárquica
        if not self.create_hierarchical_structure():
            return False
        
        # Paso 4: Bottom-Up Forecast
        self.run_bottom_up_forecast(level='store', periods=forecast_periods)
        
        # Paso 5: Top-Down Forecast
        self.run_top_down_forecast(periods=forecast_periods)
        
        # Paso 6: ARIMA Forecast
        self.run_arima_forecast(level='store', periods=forecast_periods)
        
        # Paso 6: Visualizaciones
        self.visualize_forecasts()
        
        # Paso 7: Dashboard completo
        self.create_dashboard()
        
        # Paso 9: Exportar resultados
        self.export_results()
        
        print("\n" + "="*70)
        print(" ✅ ANÁLISIS COMPLETO FINALIZADO")
        print("="*70)
        
        return True
    
    def close(self):
        """Cerrar conexión a base de datos"""
        if self.conn:
            self.conn.close()
            print("🔌 Conexión cerrada")


def main():
    """
    Función principal para ejecutar el análisis
    """
    print("\n" + "="*70)
    print("  WALMART HIERARCHICAL FORECASTING")
    print("  Análisis de Series Temporales con Reconciliación Jerárquica")
    print("="*70 + "\n")
    
    # Crear instancia
    forecaster = WalmartHierarchicalForecasting(
        server='localhost',
        database='WalmartAnalytics'
    )
    
    # Ejecutar análisis completo
    success = forecaster.run_complete_analysis(forecast_periods=7)
    
    # Cerrar conexión
    forecaster.close()
    
    if success:
        print("\n✨ Proceso completado exitosamente")
        print("📂 Revisa la carpeta 'output' para ver los resultados")
    else:
        print("\n⚠️ El proceso encontró algunos errores")
        print("💡 Verifica la conexión a SQL Server y que los datos existan")
    
    return success


if __name__ == "__main__":
    main()
