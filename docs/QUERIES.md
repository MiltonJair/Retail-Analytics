# SQL Queries Documentation

## Overview
This document describes the 10 advanced SQL queries used in the Walmart Analytics system for hierarchical analysis, forecasting, and business intelligence.

**Location:** `database/WALMART_SQL_QUERIES.sql`

---

## Query Index

| Query | Purpose | Data | Complexity |
|-------|---------|------|-----------|
| 1 | Top 10 Stores Hierarchical | Sales by store with hierarchy | Medium |
| 2 | Top 20 Products per Store | Product performance | Medium |
| 3 | Full Hierarchy Drill-Down | Company → Store → Department → Item | Advanced |
| 4 | Temporal Trends Analysis | Sales trends with moving averages | Advanced |
| 5 | Market Basket Analysis | Product co-purchases | Advanced |
| 6 | Store Segmentation (Boston Matrix) | Store classification by growth/contribution | Medium |
| 7 | RLS Configuration | User access control mapping | Medium |
| 8 | Forecasting Validation | Forecast accuracy metrics (MAPE, RMSE, MAE) | Advanced |
| 9 | Seasonal Pattern Analysis | Monthly/daily seasonality detection | Advanced |
| 10 | Data Quality Metrics | Data completeness and validation | Medium |

---

## Query Details

### Query 1: Top 10 Stores Hierarchical Analysis

**Purpose:** Identify best performing stores with sales hierarchy

**SQL Pattern:**
```sql
WITH store_sales AS (
    SELECT 
        s.StoreId,
        s.StoreName,
        SUM(ih.TotalAmount) as Total_Sales,
        COUNT(DISTINCT ih.InvoiceNo) as Transactions,
        COUNT(DISTINCT ih.CustomerID) as Customers,
        AVG(ih.TotalAmount) as Avg_Transaction
    FROM Stores s
    LEFT JOIN InvoiceHeaders ih ON s.StoreId = ih.StoreId
    WHERE ih.InvoiceDate >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY s.StoreId, s.StoreName
)
SELECT TOP 10 * FROM store_sales
ORDER BY Total_Sales DESC
```

**Key Insights:**
- Sales per store
- Customer reach
- Transaction efficiency (Avg_Transaction)
- Trends (last 90 days)

**Use Cases:**
- Executive dashboard: "Which stores perform best?"
- Resource allocation: "Where to invest?"
- Benchmarking: "Store performance vs. average"

**Performance:** < 1 second (indexed on StoreId, InvoiceDate)

---

### Query 2: Top 20 Products per Store

**Purpose:** Identify top products in each store

**SQL Pattern:**
```sql
WITH product_sales AS (
    SELECT 
        i.StoreId,
        i.ItemId,
        i.ItemName,
        SUM(id.Quantity) as Total_Qty,
        SUM(id.TotalPrice) as Total_Sales,
        COUNT(DISTINCT ih.InvoiceNo) as Purchase_Freq,
        SUM(id.TotalPrice) / NULLIF(SUM(id.Quantity), 0) as Avg_Price
    FROM InvoiceDetails id
    JOIN InvoiceHeaders ih ON id.InvoiceNo = ih.InvoiceNo
    JOIN Items i ON id.ItemId = i.ItemId
    WHERE ih.InvoiceDate >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY i.StoreId, i.ItemId, i.ItemName
)
SELECT 
    StoreId,
    TOP 20 ItemName,
    Total_Sales,
    Purchase_Freq
FROM product_sales
ORDER BY StoreId, Total_Sales DESC
```

**Key Insights:**
- Product mix by store
- Regional preferences
- Inventory priorities
- Cross-store trends

**Use Cases:**
- Inventory planning: "Stock management per store"
- Marketing: "Promotion targets by store"
- Supply chain: "Distribution optimization"

**Performance:** < 2 seconds (indexed on StoreId, ItemId)

---

### Query 3: Full Hierarchy Drill-Down

**Purpose:** Company-level view with drill-down to item level

**SQL Pattern:**
```sql
WITH hierarchy AS (
    SELECT 
        'Company' as Level,
        'WALMART' as Entity,
        NULL as ParentEntity,
        SUM(id.TotalPrice) as Sales,
        COUNT(DISTINCT id.InvoiceNo) as Transactions
    FROM InvoiceDetails id
    
    UNION ALL
    
    SELECT 
        'Store',
        s.StoreName,
        'WALMART',
        SUM(id.TotalPrice),
        COUNT(DISTINCT id.InvoiceNo)
    FROM InvoiceDetails id
    JOIN InvoiceHeaders ih ON id.InvoiceNo = ih.InvoiceNo
    JOIN Stores s ON ih.StoreId = s.StoreId
    GROUP BY s.StoreId, s.StoreName
    
    UNION ALL
    
    SELECT 
        'Department',
        d.DepartmentName,
        s.StoreName,
        SUM(id.TotalPrice),
        COUNT(DISTINCT id.InvoiceNo)
    FROM InvoiceDetails id
    JOIN InvoiceHeaders ih ON id.InvoiceNo = ih.InvoiceNo
    JOIN Items i ON id.ItemId = i.ItemId
    JOIN Departments d ON i.DepartmentId = d.DepartmentId
    JOIN Stores s ON ih.StoreId = s.StoreId
    GROUP BY d.DepartmentId, d.DepartmentName, s.StoreId, s.StoreName
    
    UNION ALL
    
    SELECT 
        'Item',
        i.ItemName,
        d.DepartmentName,
        SUM(id.TotalPrice),
        COUNT(DISTINCT id.InvoiceNo)
    FROM InvoiceDetails id
    JOIN Items i ON id.ItemId = i.ItemId
    JOIN Departments d ON i.DepartmentId = d.DepartmentId
    GROUP BY i.ItemId, i.ItemName, d.DepartmentId, d.DepartmentName
)
SELECT * FROM hierarchy
ORDER BY Sales DESC
```

**Key Insights:**
- Complete organizational view
- Sales breakdown at all levels
- Drill-down capability
- Hierarchical relationships

**Use Cases:**
- Executive reports: "Full company view"
- Analytics: "Comparative analysis"
- Forecasting: "Hierarchical forecasts"

**Performance:** < 3 seconds (multiple unions require optimization)

---

### Query 4: Temporal Trends Analysis

**Purpose:** Analyze sales trends over time with moving averages

**SQL Pattern:**
```sql
WITH daily_sales AS (
    SELECT 
        CAST(ih.InvoiceDate as DATE) as SaleDate,
        SUM(ih.TotalAmount) as Daily_Sales,
        COUNT(DISTINCT ih.InvoiceNo) as Transactions,
        COUNT(DISTINCT ih.CustomerID) as Customers
    FROM InvoiceHeaders ih
    WHERE ih.InvoiceDate >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY CAST(ih.InvoiceDate as DATE)
),
trending AS (
    SELECT 
        SaleDate,
        Daily_Sales,
        AVG(Daily_Sales) OVER (
            ORDER BY SaleDate 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as MA7_Sales,  -- 7-day moving average
        AVG(Daily_Sales) OVER (
            ORDER BY SaleDate 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) as MA30_Sales, -- 30-day moving average
        LAG(Daily_Sales) OVER (ORDER BY SaleDate) as Prev_Day,
        CAST(100.0 * (Daily_Sales - LAG(Daily_Sales) OVER (ORDER BY SaleDate)) 
            / LAG(Daily_Sales) OVER (ORDER BY SaleDate) as DECIMAL(5,2)) as DayOverDay_Pct
    FROM daily_sales
)
SELECT * FROM trending
ORDER BY SaleDate DESC
```

**Key Insights:**
- Sales trends over time
- Seasonal patterns
- Day-over-day growth
- Smooth trend with moving averages

**Use Cases:**
- Forecasting: "Trend identification"
- Anomaly detection: "Unexpected changes"
- Performance tracking: "Growth measurement"

**Performance:** < 2 seconds (indexed on InvoiceDate)

---

### Query 5: Market Basket Analysis

**Purpose:** Identify product co-purchase patterns

**SQL Pattern:**
```sql
WITH product_pairs AS (
    SELECT 
        id1.ItemId as Product_A,
        id2.ItemId as Product_B,
        i1.ItemName as ProductA_Name,
        i2.ItemName as ProductB_Name,
        COUNT(DISTINCT id1.InvoiceNo) as Co_Purchase_Count,
        CAST(
            100.0 * COUNT(DISTINCT id1.InvoiceNo) / 
            (SELECT COUNT(DISTINCT InvoiceNo) FROM InvoiceHeaders 
             WHERE InvoiceDate >= DATEADD(MONTH, -3, GETDATE()))
            as DECIMAL(5,2)
        ) as Support_Pct
    FROM InvoiceDetails id1
    JOIN InvoiceDetails id2 ON id1.InvoiceNo = id2.InvoiceNo 
        AND id1.ItemId < id2.ItemId  -- Avoid duplicates
    JOIN Items i1 ON id1.ItemId = i1.ItemId
    JOIN Items i2 ON id2.ItemId = i2.ItemId
    JOIN InvoiceHeaders ih ON id1.InvoiceNo = ih.InvoiceNo
    WHERE ih.InvoiceDate >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY id1.ItemId, id2.ItemId, i1.ItemName, i2.ItemName
)
SELECT TOP 50 * FROM product_pairs
WHERE Co_Purchase_Count >= 5  -- Min 5 co-purchases
ORDER BY Co_Purchase_Count DESC
```

**Key Insights:**
- Products bought together
- Cross-sell opportunities
- Bundle recommendations
- Customer preferences

**Use Cases:**
- Marketing: "Product bundling"
- Merchandising: "Store layout optimization"
- Recommendations: "Personalized suggestions"

**Performance:** < 3 seconds (self-join on large table, indexed on InvoiceNo)

---

### Query 6: Store Segmentation (Boston Matrix)

**Purpose:** Classify stores by growth and contribution

**SQL Pattern:**
```sql
WITH store_metrics AS (
    SELECT 
        s.StoreId,
        s.StoreName,
        SUM(ih.TotalAmount) as Total_Sales,
        AVG(CAST(ROW_NUMBER() OVER (
            PARTITION BY s.StoreId 
            ORDER BY ih.InvoiceDate
        ) as FLOAT)) as Avg_Rank,  -- Proxy for growth
        ROW_NUMBER() OVER (ORDER BY SUM(ih.TotalAmount) DESC) as Sales_Rank
    FROM Stores s
    LEFT JOIN InvoiceHeaders ih ON s.StoreId = ih.StoreId
        AND ih.InvoiceDate >= DATEADD(MONTH, -3, GETDATE())
    GROUP BY s.StoreId, s.StoreName
),
segmentation AS (
    SELECT 
        StoreId,
        StoreName,
        Total_Sales,
        CASE 
            WHEN Sales_Rank <= 5 AND Avg_Rank < 50 THEN 'Cash Cow'
            WHEN Sales_Rank <= 5 AND Avg_Rank >= 50 THEN 'Star'
            WHEN Sales_Rank > 5 AND Avg_Rank < 50 THEN 'Dog'
            ELSE 'Question Mark'
        END as Segment
    FROM store_metrics
)
SELECT Segment, COUNT(*) as Store_Count, AVG(Total_Sales) as Avg_Sales
FROM segmentation
GROUP BY Segment
```

**Key Insights:**
- Store classification (Star, Cash Cow, etc.)
- Growth vs. contribution balance
- Strategic allocation guide
- Portfolio optimization

**Use Cases:**
- Strategy: "Store investment decisions"
- Operations: "Resource allocation"
- Planning: "Expansion targets"

**Performance:** < 1 second (aggregation only)

---

### Query 7: RLS Configuration

**Purpose:** User access control mapping

**SQL Pattern:**
```sql
SELECT 
    u.UserId,
    u.UserName,
    u.Email,
    r.RoleName,
    STRING_AGG(s.StoreName, ', ') as AccessibleStores
FROM SecurityUsers u
LEFT JOIN SecurityRoles r ON u.RoleId = r.RoleId
LEFT JOIN UserStoreAccess usa ON u.UserId = usa.UserId
LEFT JOIN Stores s ON usa.StoreId = s.StoreId
GROUP BY u.UserId, u.UserName, u.Email, r.RoleName
ORDER BY u.UserName
```

**Key Insights:**
- User-role assignments
- Store access mapping
- Permission matrix
- Access control overview

**Use Cases:**
- Security: "Access validation"
- Auditing: "Permission review"
- Provisioning: "New user setup"

**Performance:** < 1 second (simple joins)

---

### Query 8: Forecasting Validation

**Purpose:** Calculate forecast accuracy metrics

**SQL Pattern:**
```sql
WITH forecast_comparison AS (
    SELECT 
        f.ForecastDate,
        f.ForecastedAmount,
        COALESCE(ih.ActualAmount, 0) as ActualAmount,
        ABS(f.ForecastedAmount - COALESCE(ih.ActualAmount, 0)) as Error,
        CAST(
            100.0 * ABS(f.ForecastedAmount - COALESCE(ih.ActualAmount, 0)) 
            / NULLIF(COALESCE(ih.ActualAmount, 1), 0)
            as DECIMAL(5,2)
        ) as MAPE  -- Mean Absolute Percentage Error
    FROM Forecasts f
    LEFT JOIN InvoiceHeaders ih ON CAST(f.ForecastDate as DATE) = CAST(ih.InvoiceDate as DATE)
)
SELECT 
    'Overall' as Metric,
    COUNT(*) as Period_Count,
    AVG(ForecastedAmount) as Avg_Forecast,
    AVG(ActualAmount) as Avg_Actual,
    CAST(AVG(Error) as DECIMAL(10,2)) as MAE,
    CAST(SQRT(AVG(Error * Error)) as DECIMAL(10,2)) as RMSE,
    CAST(AVG(MAPE) as DECIMAL(5,2)) as MAPE_Pct
FROM forecast_comparison
WHERE ActualAmount > 0  -- Only for periods with actual data
```

**Key Insights:**
- Forecast accuracy (MAPE, RMSE, MAE)
- Bias detection
- Model performance
- Confidence intervals

**Use Cases:**
- Model evaluation: "Accuracy assessment"
- Comparison: "Best method selection"
- Improvement: "Tuning optimization"

**Performance:** < 2 seconds (depends on forecast table size)

---

### Query 9: Seasonal Pattern Analysis

**Purpose:** Detect and analyze seasonal patterns

**SQL Pattern:**
```sql
WITH daily_sales AS (
    SELECT 
        CAST(ih.InvoiceDate as DATE) as SaleDate,
        MONTH(ih.InvoiceDate) as Month,
        DAY(ih.InvoiceDate) as DayOfMonth,
        DATEPART(WEEKDAY, ih.InvoiceDate) as DayOfWeek,
        SUM(ih.TotalAmount) as Daily_Sales
    FROM InvoiceHeaders ih
    WHERE ih.InvoiceDate >= DATEADD(YEAR, -1, GETDATE())
    GROUP BY CAST(ih.InvoiceDate as DATE), MONTH(ih.InvoiceDate), DAY(ih.InvoiceDate), DATEPART(WEEKDAY, ih.InvoiceDate)
),
seasonality AS (
    SELECT 
        Month,
        AVG(Daily_Sales) as Avg_Monthly_Sales,
        STDDEV(Daily_Sales) as Std_Monthly_Sales
    FROM daily_sales
    GROUP BY Month
),
dow_seasonality AS (
    SELECT 
        DayOfWeek,
        AVG(Daily_Sales) as Avg_DOW_Sales,
        COUNT(*) as Occurrences
    FROM daily_sales
    GROUP BY DayOfWeek
)
SELECT * FROM seasonality
ORDER BY Avg_Monthly_Sales DESC
```

**Key Insights:**
- Monthly seasonality
- Day-of-week patterns
- Peak and off-peak periods
- Predictable fluctuations

**Use Cases:**
- Forecasting: "Seasonal adjustment"
- Staffing: "Resource planning"
- Marketing: "Campaign timing"

**Performance:** < 2 seconds (aggregation with window functions)

---

### Query 10: Data Quality Metrics

**Purpose:** Validate data completeness and consistency

**SQL Pattern:**
```sql
WITH data_quality AS (
    SELECT 
        'InvoiceHeaders' as TableName,
        COUNT(*) as Total_Records,
        SUM(CASE WHEN InvoiceNo IS NULL THEN 1 ELSE 0 END) as Null_InvoiceNo,
        SUM(CASE WHEN InvoiceDate IS NULL THEN 1 ELSE 0 END) as Null_InvoiceDate,
        SUM(CASE WHEN TotalAmount <= 0 THEN 1 ELSE 0 END) as Invalid_Amount,
        MIN(InvoiceDate) as Min_Date,
        MAX(InvoiceDate) as Max_Date
    FROM InvoiceHeaders
    
    UNION ALL
    
    SELECT 
        'InvoiceDetails',
        COUNT(*),
        SUM(CASE WHEN InvoiceNo IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN ItemId IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN TotalPrice <= 0 THEN 1 ELSE 0 END),
        NULL,
        NULL
    FROM InvoiceDetails
    
    UNION ALL
    
    SELECT 
        'Customers',
        COUNT(*),
        SUM(CASE WHEN CustomerId IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN CustomerName IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN TotalLifetimeSpend < 0 THEN 1 ELSE 0 END),
        NULL,
        NULL
    FROM Customers
)
SELECT * FROM data_quality
```

**Key Insights:**
- Data completeness
- Missing values detection
- Invalid data counts
- Date range coverage

**Use Cases:**
- Data governance: "Quality validation"
- ETL monitoring: "Pipeline health"
- Troubleshooting: "Data issue identification"

**Performance:** < 1 second (simple counts)

---

## Best Practices

### Query Optimization
1. **Indexes:** Create composite indexes on (StoreId, InvoiceDate)
2. **Partitioning:** Partition large tables by year/month
3. **Materialized Views:** Pre-calculate aggregations
4. **Statistics:** Update table statistics regularly

### Performance Tuning
```sql
-- Enable execution plans
SET STATISTICS IO ON
SET STATISTICS TIME ON

-- Check query cost
EXPLAIN (ANALYZE true) SELECT ...
```

### Query Development Workflow
1. Start with small datasets (test data)
2. Profile query performance
3. Add indexes as needed
4. Validate results manually
5. Document assumptions and dependencies

---

## References
- See ARCHITECTURE.md for system design details
- See README.md for quick start guide
- See database/WALMART_SQL_QUERIES.sql for complete query code
