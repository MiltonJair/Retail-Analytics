"""
=============================================================================
ANALYTICS QUERIES - EJECUTAR QUERIES ANALÍTICAS
=============================================================================
Script para ejecutar queries de análisis y exportar SQL
"""

import sys
import io
import pyodbc
import pandas as pd
from datetime import datetime

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class Analytics:
    def __init__(self):
        self.connection = None
        self.db_name = 'WalmartAnalytics'
    
    def connect(self):
        """Conectar a SQL Server"""
        try:
            conn_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=localhost;DATABASE={self.db_name};Trusted_Connection=yes;'
            self.connection = pyodbc.connect(conn_string, autocommit=True)
            print(f"✓ Conectado a {self.db_name}")
            return True
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False
    
    def execute_query(self, query_name, query):
        """Ejecutar una query y retornar DataFrame"""
        try:
            df = pd.read_sql(query, self.connection)
            print(f"✓ {query_name}: {len(df)} registros")
            return df
        except Exception as e:
            print(f"✗ Error en {query_name}: {e}")
            return None
    
    def query_hourly_analysis(self):
        """Q7-D: Análisis por hora"""
        query = """
        SELECT 
            DATEPART(HOUR, ih.InvoiceDate) AS Hora,
            COUNT(DISTINCT ih.InvoiceID) AS TotalFacturas,
            SUM(ih.TotalAmount) AS VentasPorHora,
            AVG(ih.TotalAmount) AS PromedioPorFactura,
            MIN(ih.TotalAmount) AS VentaMinima,
            MAX(ih.TotalAmount) AS VentaMaxima,
            COUNT(DISTINCT ih.StoreID) AS TiendasActivas
        FROM InvoiceHeaders ih
        GROUP BY DATEPART(HOUR, ih.InvoiceDate)
        ORDER BY Hora
        """
        return self.execute_query("Q7-D: Análisis Horario", query)
    
    def query_top_products(self):
        """Q7-E: Top 20 Productos"""
        query = """
        SELECT TOP 20
            i.ItemCode,
            i.ItemName,
            d.DepartmentName,
            SUM(id.QuantitySold) AS UnidadesVendidas,
            SUM(id.LineTotal) AS IngresoTotal,
            COUNT(DISTINCT ih.InvoiceID) AS Transacciones,
            AVG(id.UnitPrice) AS PrecioPromedio
        FROM 
            Items i
            INNER JOIN Departments d ON i.DepartmentID = d.DepartmentID
            INNER JOIN InvoiceDetails id ON i.ItemID = id.ItemID
            INNER JOIN InvoiceHeaders ih ON id.InvoiceID = ih.InvoiceID
        GROUP BY 
            i.ItemID,
            i.ItemCode,
            i.ItemName,
            d.DepartmentID,
            d.DepartmentName
        ORDER BY IngresoTotal DESC
        """
        return self.execute_query("Q7-E: Top 20 Productos", query)
    
    def export_database_script(self):
        """Generar script SQL de exportación"""
        try:
            cursor = self.connection.cursor()
            
            # Obtener información de la BD
            sql_script = f"""
-- =============================================================================
-- SCRIPT DE EXPORTACIÓN: WALMART ANALYTICS DATABASE
-- Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- =============================================================================

USE master
GO

-- Crear BD si no existe
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{self.db_name}')
BEGIN
    CREATE DATABASE {self.db_name}
END
GO

USE {self.db_name}
GO

-- =============================================================================
-- TABLAS
-- =============================================================================

"""
            
            # Tabla Stores
            cursor.execute("""
                SELECT * FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'Stores' AND TABLE_TYPE = 'BASE TABLE'
            """)
            if cursor.fetchone():
                sql_script += """
-- TABLA: Stores
CREATE TABLE Stores (
    StoreID INT PRIMARY KEY IDENTITY(1,1),
    StoreName NVARCHAR(100) NOT NULL,
    City NVARCHAR(50),
    State NVARCHAR(50),
    Country NVARCHAR(50) DEFAULT 'USA',
    CreatedDate DATETIME DEFAULT GETDATE()
)
GO

"""
            
            # Tabla Departments
            sql_script += """
-- TABLA: Departments
CREATE TABLE Departments (
    DepartmentID INT PRIMARY KEY IDENTITY(1,1),
    DepartmentName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(500),
    CreatedDate DATETIME DEFAULT GETDATE()
)
GO

"""
            
            # Tabla Items
            sql_script += """
-- TABLA: Items
CREATE TABLE Items (
    ItemID INT PRIMARY KEY IDENTITY(1,1),
    ItemCode NVARCHAR(50) NOT NULL UNIQUE,
    ItemName NVARCHAR(200) NOT NULL,
    DepartmentID INT NOT NULL,
    BasePrice DECIMAL(10,2),
    CreatedDate DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID)
)
GO

"""
            
            # Tabla InvoiceHeaders
            sql_script += """
-- TABLA: InvoiceHeaders
CREATE TABLE InvoiceHeaders (
    InvoiceID INT PRIMARY KEY IDENTITY(1,1),
    StoreID INT NOT NULL,
    InvoiceDate DATETIME NOT NULL,
    TotalAmount DECIMAL(15,2),
    TotalItems INT,
    CreatedDate DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (StoreID) REFERENCES Stores(StoreID)
)
GO

"""
            
            # Tabla InvoiceDetails
            sql_script += """
-- TABLA: InvoiceDetails
CREATE TABLE InvoiceDetails (
    DetailID INT PRIMARY KEY IDENTITY(1,1),
    InvoiceID INT NOT NULL,
    ItemID INT NOT NULL,
    QuantitySold INT,
    UnitPrice DECIMAL(10,2),
    LineTotal DECIMAL(15,2),
    CreatedDate DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (InvoiceID) REFERENCES InvoiceHeaders(InvoiceID),
    FOREIGN KEY (ItemID) REFERENCES Items(ItemID)
)
GO

"""
            
            # Datos
            cursor.execute("SELECT COUNT(*) FROM Stores")
            store_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM InvoiceHeaders")
            invoice_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM InvoiceDetails")
            detail_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(TotalAmount) FROM InvoiceHeaders")
            total_sales = cursor.fetchone()[0]
            
            sql_script += f"""
-- =============================================================================
-- ESTADÍSTICAS DE DATOS
-- =============================================================================

-- Stores: {store_count} registros
-- Departments: 7 registros
-- Items: 15 registros
-- InvoiceHeaders: {invoice_count} registros
-- InvoiceDetails: {detail_count} registros
-- Total Ventas: ${total_sales:.2f}

-- =============================================================================
-- FIN DEL SCRIPT
-- =============================================================================
"""
            
            # Guardar script
            output_file = r'c:\Users\indie\Nueva carpeta\database\03_export_database_python.sql'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(sql_script)
            
            print(f"✓ Script exportado: {output_file}")
            print(f"  - Stores: {store_count}")
            print(f"  - Facturas: {invoice_count}")
            print(f"  - Detalles: {detail_count}")
            print(f"  - Total Ventas: ${total_sales:.2f}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error exportando: {e}")
            return False

def main():
    print("=" * 70)
    print("ANALYTICS QUERIES - ANÁLISIS Y EXPORTACIÓN")
    print("=" * 70)
    
    analytics = Analytics()
    
    if not analytics.connect():
        return
    
    print("\n🔍 Ejecutando queries analíticas...")
    
    # Ejecutar queries
    df_hourly = analytics.query_hourly_analysis()
    df_top_products = analytics.query_top_products()
    
    # Exportar script
    print("\n💾 Exportando script SQL...")
    analytics.export_database_script()
    
    print("\n" + "=" * 70)
    print("✓ ANALYTICS COMPLETADAS")
    print("=" * 70)
    
    if analytics.connection:
        analytics.connection.close()

if __name__ == '__main__':
    main()
