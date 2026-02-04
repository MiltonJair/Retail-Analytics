-- ==================================================================================
-- WALMART ANALYTICS - SQL QUERIES AVANZADAS
-- Queries complejas para análisis jerárquico, segmentación y forecasting
-- ==================================================================================

-- ==================================================================================
-- QUERY 1: TOP 10 TIENDAS CON ANÁLISIS JERÁRQUICO Y RANKING
-- ==================================================================================
-- Objetivo: Identificar top 10 tiendas por total de ventas con análisis departamental
-- y ranking por performance tier
-- Métrica de negocio: Priorizar tiendas high-performing para enfoque operacional

SELECT TOP 10
    s.StoreID,
    s.StoreName,
    s.City,
    s.State,
    COUNT(DISTINCT id.InvoiceID) AS TotalTransacciones,
    COUNT(DISTINCT id.ProductID) AS ProductosVendidos,
    COUNT(DISTINCT id.Quantity) AS UnidadesVendidas,
    CAST(SUM(id.Quantity * p.Price) AS DECIMAL(12,2)) AS TotalVentas,
    CAST(AVG(id.Quantity * p.Price) AS DECIMAL(10,2)) AS TicketPromedio,
    CAST(STDEV(id.Quantity * p.Price) AS DECIMAL(10,2)) AS StdDevVentas,
    CASE 
        WHEN RANK() OVER (ORDER BY SUM(id.Quantity * p.Price) DESC) <= 3 THEN 'Tier-1 Premium'
        WHEN RANK() OVER (ORDER BY SUM(id.Quantity * p.Price) DESC) <= 7 THEN 'Tier-2 Standard'
        ELSE 'Tier-3 Monitor'
    END AS PerformanceTier,
    DATEDIFF(DAY, MIN(id.InvoiceDate), MAX(id.InvoiceDate)) + 1 AS DiasCon Actividad,
    CAST(100.0 * SUM(id.Quantity * p.Price) / 
        (SELECT SUM(id2.Quantity * p2.Price) FROM InvoiceDetails id2 
         JOIN Products p2 ON id2.ProductID = p2.ProductID) AS DECIMAL(5,2)) AS PorcentajeTotalVentas
FROM Stores s
    JOIN Invoices i ON s.StoreID = i.StoreID
    JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
    JOIN Products p ON id.ProductID = p.ProductID
GROUP BY s.StoreID, s.StoreName, s.City, s.State
ORDER BY TotalVentas DESC;

-- ==================================================================================
-- QUERY 2: TOP 20 PRODUCTOS POR TIENDA CON ANÁLISIS DE PENETRACIÓN
-- ==================================================================================
-- Objetivo: Identificar top productos por tienda + % tiendas que los venden
-- Métrica de negocio: Determinar productos core vs niche por geografía

WITH ProductosPorTienda AS (
    SELECT 
        p.ProductID,
        p.ProductName,
        s.StoreID,
        s.StoreName,
        SUM(id.Quantity) AS UnidadesVendidas,
        CAST(SUM(id.Quantity * p.Price) AS DECIMAL(12,2)) AS TotalVentas,
        ROW_NUMBER() OVER (PARTITION BY s.StoreID ORDER BY SUM(id.Quantity * p.Price) DESC) AS RankEnTienda
    FROM Products p
        JOIN InvoiceDetails id ON p.ProductID = id.ProductID
        JOIN Invoices i ON id.InvoiceID = i.InvoiceID
        JOIN Stores s ON i.StoreID = s.StoreID
    GROUP BY p.ProductID, p.ProductName, s.StoreID, s.StoreName
),
PenetrationStats AS (
    SELECT 
        ProductID,
        ProductName,
        COUNT(DISTINCT StoreID) AS TiendasVenden,
        CAST(100.0 * COUNT(DISTINCT StoreID) / (SELECT COUNT(DISTINCT StoreID) FROM Stores) AS DECIMAL(5,2)) AS PorcentajeTiendas
    FROM ProductosPorTienda
    GROUP BY ProductID, ProductName
)
SELECT TOP 20
    ppt.ProductID,
    ppt.ProductName,
    ppt.StoreID,
    ppt.StoreName,
    ppt.RankEnTienda,
    ppt.UnidadesVendidas,
    ppt.TotalVentas,
    ps.TiendasVenden,
    ps.PorcentajeTiendas,
    CASE 
        WHEN ps.PorcentajeTiendas >= 80 THEN 'Producto Masivo'
        WHEN ps.PorcentajeTiendas >= 50 THEN 'Producto Regional'
        ELSE 'Producto Niche'
    END AS CategoriaDistribucion
FROM ProductosPorTienda ppt
    JOIN PenetrationStats ps ON ppt.ProductID = ps.ProductID
WHERE ppt.RankEnTienda <= 20
ORDER BY ppt.TotalVentas DESC;

-- ==================================================================================
-- QUERY 3: ANÁLISIS JERÁRQUICO: DEPARTAMENTO → TIENDA → PRODUCTO
-- ==================================================================================
-- Objetivo: Árbol jerárquico completo de ventas con agregaciones en todos niveles
-- Métrica de negocio: Drilldown completo para análisis granular

WITH HierarchicalSales AS (
    SELECT 
        NULL AS ProductID,
        NULL AS ProductName,
        d.DepartmentID,
        d.DepartmentName,
        NULL AS StoreID,
        NULL AS StoreName,
        1 AS HierarchyLevel,  -- Nivel 1: Departamento
        SUM(id.Quantity * p.Price) AS TotalVentas,
        SUM(id.Quantity) AS TotalUnidades,
        COUNT(DISTINCT id.InvoiceID) AS TransaccionesTotales
    FROM Departments d
        JOIN Products p ON d.DepartmentID = p.DepartmentID
        JOIN InvoiceDetails id ON p.ProductID = id.ProductID
    GROUP BY d.DepartmentID, d.DepartmentName
    
    UNION ALL
    
    SELECT 
        NULL AS ProductID,
        NULL AS ProductName,
        d.DepartmentID,
        d.DepartmentName,
        s.StoreID,
        s.StoreName,
        2 AS HierarchyLevel,  -- Nivel 2: Departamento-Tienda
        SUM(id.Quantity * p.Price) AS TotalVentas,
        SUM(id.Quantity) AS TotalUnidades,
        COUNT(DISTINCT id.InvoiceID) AS TransaccionesTotales
    FROM Departments d
        JOIN Products p ON d.DepartmentID = p.DepartmentID
        JOIN InvoiceDetails id ON p.ProductID = id.ProductID
        JOIN Invoices i ON id.InvoiceID = i.InvoiceID
        JOIN Stores s ON i.StoreID = s.StoreID
    GROUP BY d.DepartmentID, d.DepartmentName, s.StoreID, s.StoreName
    
    UNION ALL
    
    SELECT 
        p.ProductID,
        p.ProductName,
        d.DepartmentID,
        d.DepartmentName,
        s.StoreID,
        s.StoreName,
        3 AS HierarchyLevel,  -- Nivel 3: Producto
        SUM(id.Quantity * p.Price) AS TotalVentas,
        SUM(id.Quantity) AS TotalUnidades,
        COUNT(DISTINCT id.InvoiceID) AS TransaccionesTotales
    FROM Departments d
        JOIN Products p ON d.DepartmentID = p.DepartmentID
        JOIN InvoiceDetails id ON p.ProductID = id.ProductID
        JOIN Invoices i ON id.InvoiceID = i.InvoiceID
        JOIN Stores s ON i.StoreID = s.StoreID
    GROUP BY p.ProductID, p.ProductName, d.DepartmentID, d.DepartmentName, s.StoreID, s.StoreName
)
SELECT 
    HierarchyLevel,
    DepartmentID,
    DepartmentName,
    StoreID,
    StoreName,
    ProductID,
    ProductName,
    TotalVentas,
    TotalUnidades,
    TransaccionesTotales,
    CAST(TotalVentas / NULLIF(TransaccionesTotales, 0) AS DECIMAL(10,2)) AS TicketPromedio,
    ROW_NUMBER() OVER (PARTITION BY HierarchyLevel, DepartmentID, StoreID ORDER BY TotalVentas DESC) AS RankingLocal
FROM HierarchicalSales
ORDER BY HierarchyLevel, DepartmentID, TotalVentas DESC;

-- ==================================================================================
-- QUERY 4: ANÁLISIS DE TENDENCIA TEMPORAL CON MOVING AVERAGE
-- ==================================================================================
-- Objetivo: Detectar tendencias, estacionalidad y cambios en momentum de ventas
-- Métrica de negocio: Identificar periodos anómalos, picos de demanda, caídas

SELECT 
    CAST(i.InvoiceDate AS DATE) AS Fecha,
    SUM(id.Quantity * p.Price) AS VentasDiarias,
    CAST(AVG(SUM(id.Quantity * p.Price)) OVER (
        ORDER BY CAST(i.InvoiceDate AS DATE) 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS DECIMAL(12,2)) AS MA7_VentasPromedio,
    CAST(AVG(SUM(id.Quantity * p.Price)) OVER (
        ORDER BY CAST(i.InvoiceDate AS DATE) 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS DECIMAL(12,2)) AS MA30_VentasPromedio,
    CAST((SUM(id.Quantity * p.Price) - AVG(SUM(id.Quantity * p.Price)) OVER (
        ORDER BY CAST(i.InvoiceDate AS DATE) 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )) / NULLIF(AVG(SUM(id.Quantity * p.Price)) OVER (
        ORDER BY CAST(i.InvoiceDate AS DATE) 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 0) * 100 AS DECIMAL(7,2)) AS DesviacionMA7Pct,
    DAY(i.InvoiceDate) AS DiaDelMes,
    DATEPART(QUARTER, i.InvoiceDate) AS Trimestre,
    CASE WHEN DAY(i.InvoiceDate) IN (1, 15, 30) THEN 'PayDay' ELSE 'Regular' END AS TipoDia
FROM Invoices i
    JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
    JOIN Products p ON id.ProductID = p.ProductID
GROUP BY CAST(i.InvoiceDate AS DATE), DAY(i.InvoiceDate), DATEPART(QUARTER, i.InvoiceDate)
ORDER BY Fecha;

-- ==================================================================================
-- QUERY 5: ANÁLISIS DE BASKET: PRODUCTOS FRECUENTEMENTE COMPRADOS JUNTOS
-- ==================================================================================
-- Objetivo: Identificar cross-sell opportunities mediante análisis de canastas
-- Métrica de negocio: Optimizar recomendaciones de productos y bundle strategies

WITH InvoiceBaskets AS (
    SELECT 
        id.InvoiceID,
        id.ProductID,
        p.ProductName,
        d.DepartmentID,
        d.DepartmentName,
        id.Quantity,
        id.Quantity * p.Price AS LineTotal
    FROM InvoiceDetails id
        JOIN Products p ON id.ProductID = p.ProductID
        JOIN Departments d ON p.DepartmentID = d.DepartmentID
),
ProductPairs AS (
    SELECT 
        ib1.ProductID AS Producto1,
        ib1.ProductName AS NombreProducto1,
        ib1.DepartmentID AS Dept1,
        ib1.DepartmentName AS DeptName1,
        ib2.ProductID AS Producto2,
        ib2.ProductName AS NombreProducto2,
        ib2.DepartmentID AS Dept2,
        ib2.DepartmentName AS DeptName2,
        COUNT(DISTINCT ib1.InvoiceID) AS ComprasConjuntas,
        CAST(SUM(ib1.LineTotal) AS DECIMAL(10,2)) AS VentasProducto1,
        CAST(SUM(ib2.LineTotal) AS DECIMAL(10,2)) AS VentasProducto2,
        CAST(SUM(ib1.LineTotal + ib2.LineTotal) AS DECIMAL(12,2)) AS VentasConjuntas,
        ROW_NUMBER() OVER (PARTITION BY ib1.ProductID ORDER BY COUNT(DISTINCT ib1.InvoiceID) DESC) AS RankingPorProducto
    FROM InvoiceBaskets ib1
        JOIN InvoiceBaskets ib2 ON ib1.InvoiceID = ib2.InvoiceID 
            AND ib1.ProductID < ib2.ProductID
    GROUP BY ib1.ProductID, ib1.ProductName, ib1.DepartmentID, ib1.DepartmentName,
             ib2.ProductID, ib2.ProductName, ib2.DepartmentID, ib2.DepartmentName
)
SELECT 
    Producto1,
    NombreProducto1,
    DeptName1,
    Producto2,
    NombreProducto2,
    DeptName2,
    ComprasConjuntas,
    VentasProducto1,
    VentasProducto2,
    VentasConjuntas,
    CASE 
        WHEN Dept1 = Dept2 THEN 'Mismo Departamento'
        ELSE 'Departamentos Diferentes'
    END AS TipoAsociacion
FROM ProductPairs
WHERE RankingPorProducto <= 5 AND ComprasConjuntas >= 3
ORDER BY ComprasConjuntas DESC;

-- ==================================================================================
-- QUERY 6: SEGMENTACIÓN DE TIENDAS POR PERFORMANCE Y POTENCIAL
-- ==================================================================================
-- Objetivo: Segmentar tiendas para estrategias diferenciadas
-- Métrica de negocio: Allocate resources y ejecutar estrategias según segmento

WITH StoreMetrics AS (
    SELECT 
        s.StoreID,
        s.StoreName,
        s.City,
        s.State,
        COUNT(DISTINCT i.InvoiceID) AS TotalTransacciones,
        COUNT(DISTINCT id.ProductID) AS ProductosDiferentes,
        CAST(SUM(id.Quantity * p.Price) AS DECIMAL(12,2)) AS TotalVentas,
        CAST(AVG(id.Quantity * p.Price) AS DECIMAL(10,2)) AS TicketPromedio,
        CAST(STDEV(id.Quantity * p.Price) AS DECIMAL(10,2)) AS Volatilidad,
        MIN(i.InvoiceDate) AS PrimeraVenta,
        MAX(i.InvoiceDate) AS UltimaVenta,
        COUNT(DISTINCT CAST(i.InvoiceDate AS DATE)) AS DiasActivos,
        DATEDIFF(DAY, MIN(i.InvoiceDate), MAX(i.InvoiceDate)) + 1 AS PeriodoTotal
    FROM Stores s
        LEFT JOIN Invoices i ON s.StoreID = i.StoreID
        LEFT JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
        LEFT JOIN Products p ON id.ProductID = p.ProductID
    GROUP BY s.StoreID, s.StoreName, s.City, s.State
),
StoreRanking AS (
    SELECT 
        *,
        PERCENT_RANK() OVER (ORDER BY TotalVentas) AS VentasPercentil,
        PERCENT_RANK() OVER (ORDER BY TicketPromedio) AS TicketPercentil,
        PERCENT_RANK() OVER (ORDER BY DiasActivos DESC) AS ConsistenciaPercentil
    FROM StoreMetrics
)
SELECT 
    StoreID,
    StoreName,
    City,
    State,
    TotalVentas,
    TicketPromedio,
    TotalTransacciones,
    ProductosDiferentes,
    DiasActivos,
    CAST(100.0 * DiasActivos / NULLIF(PeriodoTotal, 0) AS DECIMAL(5,2)) AS TasaActivacionPct,
    CASE 
        WHEN VentasPercentil >= 0.75 AND ConsistenciaPercentil >= 0.75 THEN 'Stars - Alto Desempeño'
        WHEN VentasPercentil >= 0.50 AND ConsistenciaPercentil >= 0.50 THEN 'Cash Cows - Estable'
        WHEN VentasPercentil >= 0.25 THEN 'Question Marks - Potencial'
        ELSE 'Dogs - Bajo Desempeño'
    END AS SegmentoStrategia
FROM StoreRanking
ORDER BY TotalVentas DESC;

-- ==================================================================================
-- QUERY 7: ROL LEVEL SECURITY (RLS) - CONFIGURACIÓN DE PERMISOS POR REGIÓN
-- ==================================================================================
-- Objetivo: Base para implementar RLS - cada usuario ve solo sus tiendas asignadas
-- Nota: Este es el script para preparar el schema; la aplicación de RLS en Power BI/Tableau
--       usaría esta tabla para filtrar dinámicamente según usuario logueado

-- Crear tabla de mapeo Usuario-Tienda (comentado - usar solo para setup)
-- CREATE TABLE UserStoreAccess (
--     UserID INT,
--     UserName NVARCHAR(100),
--     StoreID INT,
--     StoreName NVARCHAR(100),
--     Region NVARCHAR(50),
--     AccessLevel NVARCHAR(20), -- 'View', 'Edit', 'Admin'
--     FOREIGN KEY (StoreID) REFERENCES Stores(StoreID)
-- );

-- Query para demostrar el concepto de RLS
SELECT 
    s.StoreID,
    s.StoreName,
    s.State AS Region,
    'Regional Manager - ' + s.State AS UsuarioRolAsignado,
    'Able to see all transactions for assigned region' AS PermisosAsignados,
    COUNT(DISTINCT i.InvoiceID) AS TransaccionesVisibles,
    CAST(SUM(id.Quantity * p.Price) AS DECIMAL(12,2)) AS VentasVisibles
FROM Stores s
    LEFT JOIN Invoices i ON s.StoreID = i.StoreID
    LEFT JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
    LEFT JOIN Products p ON id.ProductID = p.ProductID
GROUP BY s.StoreID, s.StoreName, s.State
ORDER BY s.State, s.StoreName;

-- ==================================================================================
-- QUERY 8: FORECASTING - HISTÓRICO VS PREDICCIÓN (Para validar algoritmos)
-- ==================================================================================
-- Objetivo: Base de datos para validar accuracy de forecasting algorithms
-- Métrica de negocio: Medir MAPE, RMSE, MAE de predicciones vs actuals

SELECT 
    CAST(i.InvoiceDate AS DATE) AS Fecha,
    DATEPART(WEEK, i.InvoiceDate) AS NumeroSemana,
    SUM(id.Quantity * p.Price) AS VentasReales,
    NULL AS VentasPronosticadas,  -- Populated by Python/forecasting engine
    NULL AS MetodoPronostico,
    NULL AS MAPE,
    NULL AS RMSE,
    NULL AS MAE
FROM Invoices i
    JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
    JOIN Products p ON id.ProductID = p.ProductID
GROUP BY CAST(i.InvoiceDate AS DATE), DATEPART(WEEK, i.InvoiceDate)
ORDER BY Fecha;

-- ==================================================================================
-- QUERY 9: ANÁLISIS ESTACIONAL - DETECTAR PATRONES REPEAT
-- ==================================================================================
-- Objetivo: Identificar patrones semanales/mensuales para seasonality modeling
-- Métrica de negocio: Input para SARIMA y seasonal forecasting

SELECT 
    DATEPART(MONTH, i.InvoiceDate) AS Mes,
    DATEPART(WEEK, i.InvoiceDate) AS Semana,
    DATEPART(WEEKDAY, i.InvoiceDate) AS DiaSemana,
    COUNT(DISTINCT i.InvoiceID) AS TransaccionesPromedio,
    CAST(AVG(id.Quantity * p.Price) AS DECIMAL(10,2)) AS TicketPromedio,
    CAST(STDEV(id.Quantity * p.Price) AS DECIMAL(10,2)) AS StdDev,
    CAST(
        (STDEV(id.Quantity * p.Price) / AVG(id.Quantity * p.Price)) * 100 
        AS DECIMAL(5,2)
    ) AS CoeficienteVariacionPct,
    CASE 
        WHEN DATEPART(WEEKDAY, i.InvoiceDate) IN (1, 7) THEN 'Weekend'
        ELSE 'Weekday'
    END AS TipoDia,
    CASE 
        WHEN DATEPART(MONTH, i.InvoiceDate) IN (7, 8) THEN 'High Season'
        WHEN DATEPART(MONTH, i.InvoiceDate) IN (9) THEN 'Transition'
        ELSE 'Regular'
    END AS EstacionalidadEstimada
FROM Invoices i
    JOIN InvoiceDetails id ON i.InvoiceID = id.InvoiceID
    JOIN Products p ON id.ProductID = p.ProductID
GROUP BY DATEPART(MONTH, i.InvoiceDate), DATEPART(WEEK, i.InvoiceDate), 
         DATEPART(WEEKDAY, i.InvoiceDate)
ORDER BY Mes, Semana, DiaSemana;

-- ==================================================================================
-- QUERY 10: DATA QUALITY METRICS - VALIDAR INTEGRIDAD
-- ==================================================================================
-- Objetivo: Monitoreo continuo de calidad de datos para pipeline confiable
-- Métrica de negocio: Alertas para inconsistencias, datos faltantes, anomalías

SELECT 
    'Stores' AS Tabla,
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT StoreID) AS RegUnico,
    COUNT(CASE WHEN StoreName IS NULL THEN 1 END) AS NullCount,
    NULL AS MaxDate,
    NULL AS MinDate
FROM Stores

UNION ALL

SELECT 
    'Products' AS Tabla,
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT ProductID) AS RegUnico,
    COUNT(CASE WHEN ProductName IS NULL THEN 1 END) AS NullCount,
    NULL AS MaxDate,
    NULL AS MinDate
FROM Products

UNION ALL

SELECT 
    'InvoiceDetails' AS Tabla,
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT InvoiceID) AS RegUnico,
    COUNT(CASE WHEN Quantity IS NULL OR Price IS NULL THEN 1 END) AS NullCount,
    NULL AS MaxDate,
    NULL AS MinDate
FROM InvoiceDetails

UNION ALL

SELECT 
    'Invoices' AS Tabla,
    COUNT(*) AS TotalRegistros,
    COUNT(DISTINCT InvoiceID) AS RegUnico,
    COUNT(CASE WHEN InvoiceDate IS NULL THEN 1 END) AS NullCount,
    MAX(InvoiceDate) AS MaxDate,
    MIN(InvoiceDate) AS MinDate
FROM Invoices;
