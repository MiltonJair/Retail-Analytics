# Walmart Analytics - Interview Technical Questions & Answers

## Overview
This document contains 100 technical questions and comprehensive answers spanning database design, analytics, forecasting, security, and software architecture.

---

## Table of Contents
1. [Database Design (Q1-Q15)](#database-design)
2. [SQL & Queries (Q16-Q30)](#sql--queries)
3. [Data Analytics (Q31-Q50)](#data-analytics)
4. [Forecasting (Q51-Q65)](#forecasting)
5. [Security & RLS (Q66-Q80)](#security--rls)
6. [Python & Development (Q81-Q100)](#python--development)

---

## Database Design

### Q1: What is the overall database schema?

**Answer:**
The WalmartAnalytics database consists of 7 core tables with hierarchical structure:

1. **Stores** - 20 physical store locations
2. **Departments** - 7 product categories
3. **Items** - 26 SKUs (products)
4. **InvoiceHeaders** - 10,619+ transactions
5. **InvoiceDetails** - Line items per transaction
6. **Customers** - 47 active customer records
7. **RLS Tables** - SecurityUsers, SecurityRoles, UserStoreAccess, AuditLog

```
┌─────────────────┐
│    Stores (20)  │
└────────┬────────┘
         │ 1-to-many
         ↓
┌─────────────────────┐    ┌──────────────────┐
│ InvoiceHeaders      │───→│  Customers (47)  │
│   (10,619+)         │    └──────────────────┘
└────────┬────────────┘
         │ 1-to-many
         ↓
┌─────────────────────────┐
│   InvoiceDetails        │
│  (line items)           │
└────────┬────────────────┘
         │ FK-ItemId
         ↓
┌─────────────────┐
│  Items (26)     │
└────────┬────────┘
         │ FK-DepartmentId
         ↓
┌──────────────────┐
│ Departments (7)  │
└──────────────────┘

Security Tables:
├─ SecurityUsers
├─ SecurityRoles
├─ UserStoreAccess
└─ AuditLog
```

---

### Q2: What are the key design decisions and why?

**Answer:**

| Decision | Rationale |
|----------|-----------|
| **Star Schema** | Fast joins, efficient aggregations for OLAP |
| **Dimensional Hierarchy** | Company → Store → Department → Item for drill-downs |
| **Denormalization** | TotalAmount in InvoiceHeaders avoids SUM joins |
| **Customer Table** | Separate for RFM and Churn analysis |
| **RLS Architecture** | Row-level security for 700+ users with StoreId filtering |
| **Date Indexing** | Critical for time-series forecasting and trending |
| **Composite Keys** | (StoreId, InvoiceDate) for efficient range queries |

---

### Q3: How is data quality ensured?

**Answer:**

**Data Quality Metrics (Query 10):**
- Null value detection
- Negative/zero amount validation
- Date range verification
- Duplicate record detection
- Foreign key integrity checks

**Validation Procedures:**
```sql
-- Check for orphaned invoices
SELECT COUNT(*) FROM InvoiceDetails id
WHERE NOT EXISTS (SELECT 1 FROM InvoiceHeaders ih WHERE id.InvoiceNo = ih.InvoiceNo)

-- Check customer-invoice links
SELECT COUNT(*) FROM InvoiceHeaders 
WHERE CustomerID NOT IN (SELECT CustomerId FROM Customers)

-- Validate date ranges
SELECT COUNT(*) FROM InvoiceHeaders
WHERE InvoiceDate < '2019-07-01' OR InvoiceDate > '2019-09-30'
```

---

### Q4: What indexes are created and why?

**Answer:**

```sql
-- Primary Indexes (on PK)
CREATE CLUSTERED INDEX idx_stores_pk ON Stores(StoreId)
CREATE CLUSTERED INDEX idx_items_pk ON Items(ItemId)
CREATE CLUSTERED INDEX idx_customers_pk ON Customers(CustomerId)

-- Performance Indexes
CREATE INDEX idx_invoice_store_date ON InvoiceHeaders(StoreId, InvoiceDate)
CREATE INDEX idx_invoice_customer ON InvoiceHeaders(CustomerID)
CREATE INDEX idx_details_invoice ON InvoiceDetails(InvoiceNo)
CREATE INDEX idx_details_item ON InvoiceDetails(ItemId)
CREATE INDEX idx_items_department ON Items(DepartmentId)

-- RLS Indexes
CREATE INDEX idx_user_store_access ON UserStoreAccess(UserId, StoreId)
CREATE INDEX idx_audit_user_date ON AuditLog(UserId, Timestamp)
```

**Rationale:**
- Composite (StoreId, InvoiceDate): Range queries for time-series
- Foreign key indexes: Optimize joins
- RLS indexes: Fast permission lookups
- Covering indexes: Avoid table lookups

---

### Q5: How is the data volume handled (10,619+ transactions)?

**Answer:**

**Scalability Strategy:**

1. **Table Partitioning**
   - Partition InvoiceHeaders by YEAR/MONTH
   - Archive historical data to separate filegroups
   - Enables parallel query execution

2. **Materialized Views**
   - Pre-calculate daily aggregations
   - Store monthly summaries
   - Refresh during off-peak hours

3. **Indexing Strategy**
   - Composite indexes on (StoreId, Date)
   - Filtered indexes for "Active" transactions
   - Skip cold data partitions in queries

4. **Query Optimization**
   - Use approximate counts (APPROX_COUNT_DISTINCT)
   - Aggregate incrementally (Bottom-Up forecasting)
   - Avoid SELECT * in production

5. **Archival**
   - Move data > 2 years to archive tables
   - Maintain hot data in primary database
   - Support historical queries via linked servers

---

### Q6: What is a fact and dimension table? How are they used?

**Answer:**

**Dimension Tables (Slowly Changing):**
- Stores, Departments, Items, Customers
- Contain descriptive attributes
- Rarely updated (Type 1 SCD)
- Enable drill-down analysis

**Fact Tables (Rapidly Changing):**
- InvoiceHeaders, InvoiceDetails
- Contain transactions and measurements
- Foreign keys to dimensions
- Support aggregations and analytics

**Usage in Star Schema:**
```
Facts (InvoiceDetails) join to:
├─ Stores Dimension (WHERE StoreId = ?)
├─ Items Dimension (WHERE ItemId = ?)
└─ Departments Dimension (WHERE DepartmentId = ?)
```

**Benefit:**
- Normalized dimensions prevent data redundancy
- Denormalized facts enable fast aggregations
- Hierarchical dimensions support drill-down

---

### Q7: How would you handle new data ingestion?

**Answer:**

**ETL Pipeline:**

```
New Data File
    ↓
[1] Staging
    - Load to staging tables
    - Raw data unchanged
    ↓
[2] Validation
    - Check nulls, duplicates, date ranges
    - Flag invalid records
    ↓
[3] Transformation
    - Calculate derived columns (DayOfWeek, Quarter)
    - Standardize formats
    - Hash PII fields (optional)
    ↓
[4] Integration
    - Merge to production tables (UPSERT)
    - Update calculated columns
    - Insert into Customer Analytics tables
    ↓
[5] Quality Check
    - Row counts match
    - No orphaned records
    - Date ranges valid
    ↓
[6] Archive
    - Move staging to archive
    - Backup production
```

**Python Implementation:**
```python
import pyodbc
import pandas as pd

def ingest_data(csv_file):
    # Read data
    df = pd.read_csv(csv_file)
    
    # Validate
    assert df.isnull().sum().sum() == 0, "Null values found"
    
    # Transform
    df['LoadDate'] = pd.Timestamp.now()
    
    # Load to database
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    for index, row in df.iterrows():
        cursor.execute(INSERT_QUERY, tuple(row))
    
    conn.commit()
```

---

### Q8: What storage recommendations would you make for 1TB+ of data?

**Answer:**

**Storage Architecture:**

| Layer | Technology | Use Case |
|-------|-----------|----------|
| **Hot (Recent Data)** | SQL Server SSD | Last 6 months, active queries |
| **Warm (6-24 months)** | SQL Server HDD | Partitioned, archived tables |
| **Cold (>24 months)** | Azure Blob Storage | Backup, compliance, rare access |
| **Real-time Feed** | Event Hubs / Kafka | Streaming IoT/POS data |

**Recommended Setup:**

1. **SQL Server Configuration**
   ```sql
   -- Primary filegroup (SSD)
   ALTER DATABASE WalmartAnalytics ADD FILE (...)
   
   -- Archive filegroup (HDD)
   ALTER DATABASE WalmartAnalytics ADD FILE (...) TO FILEGROUP Archive
   
   -- Partition by date
   CREATE PARTITION SCHEME By_Year
   CREATE PARTITION FUNCTION By_Year (DATETIME2) 
   AS RANGE RIGHT (...)
   ```

2. **Cloud Integration (Recommended for 1TB+)**
   ```
   Azure SQL Database
   ├─ DTU: Premium tier (P4+)
   ├─ Storage: 500GB-1TB
   ├─ Backup: Geo-redundant
   ├─ Scaling: Auto-scale storage
   └─ Security: Transparent encryption (TDE)
   
   Azure Data Lake
   ├─ Archive: Cold data (< $1/TB/year)
   ├─ Analytics: Synapse SQL pool
   └─ ML: Integration with Azure ML
   ```

3. **Partitioning Strategy**
   ```sql
   -- Partition InvoiceHeaders by year
   PARTITION 2019: Q1-Q4 data
   PARTITION 2020: Q1-Q4 data
   PARTITION 2021: ...
   
   Benefits:
   - Faster queries (skip irrelevant partitions)
   - Easier maintenance (rebuild one partition)
   - Parallel operations
   ```

---

### Q9: How would you design for 100+ concurrent users?

**Answer:**

**Concurrency Optimization:**

1. **Connection Pooling**
   ```python
   # Use connection pooling to reuse connections
   pool = pyodbc.pool.SimpleConnectionPool(
       minconn=10,  # Min connections
       maxconn=100, # Max connections
       dsn='WalmartAnalytics',
       autocommit=False
   )
   ```

2. **Query Optimization**
   - Use execution plans to identify bottlenecks
   - Create covering indexes to avoid table lookups
   - Use appropriate transaction isolation levels

3. **Caching Strategy**
   ```python
   @st.cache_data(ttl=300)  # Cache for 5 minutes
   def get_store_sales():
       return query_database("SELECT ... FROM Stores")
   ```

4. **Resource Limits**
   ```sql
   -- Create resource pool for analytics queries
   CREATE WORKLOAD GROUP analytics_group
   USING default_pool
   WITH (REQUEST_MAX_CPU_TIME_SEC = 60)
   ```

5. **Load Balancing**
   - Read replicas for reporting queries
   - Primary database for transactional writes
   - Queue long-running queries

---

### Q10: What are referential integrity constraints?

**Answer:**

**Foreign Keys Defined:**

```sql
-- Store to InvoiceHeader
ALTER TABLE InvoiceHeaders
ADD CONSTRAINT fk_invoice_store FOREIGN KEY (StoreId) REFERENCES Stores(StoreId)

-- Item to Department
ALTER TABLE Items
ADD CONSTRAINT fk_item_dept FOREIGN KEY (DepartmentId) REFERENCES Departments(DepartmentId)

-- InvoiceDetail to InvoiceHeader
ALTER TABLE InvoiceDetails
ADD CONSTRAINT fk_detail_invoice FOREIGN KEY (InvoiceNo) REFERENCES InvoiceHeaders(InvoiceNo)

-- InvoiceDetail to Item
ALTER TABLE InvoiceDetails
ADD CONSTRAINT fk_detail_item FOREIGN KEY (ItemId) REFERENCES Items(ItemId)

-- InvoiceHeader to Customer
ALTER TABLE InvoiceHeaders
ADD CONSTRAINT fk_invoice_customer FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerId)
```

**Benefits:**
- Prevents orphaned records
- Maintains data consistency
- Enforces business rules at database level

---

### Q11-Q15: Additional Database Design Questions

(Due to length, abbreviated)

**Q11:** How would you handle updates to product names or store locations?
**A:** Use Slowly Changing Dimension (SCD) Type 2 - maintain version history with valid_from/valid_to dates

**Q12:** What about handling currency conversions for multiple countries?
**A:** Store amount in base currency (USD), add exchange rate table with date-based lookups

**Q13:** How to handle product discontinuation?
**A:** Add IsActive flag, use soft deletes, maintain historical data for analysis

**Q14:** What about inventory management?
**A:** Add InventoryBalances table, track by Store-Item-Date, calculate stock levels

**Q15:** How to implement audit trails for compliance?
**A:** AuditLog table tracks WHO, WHAT, WHEN, WHERE for all data changes

---

## SQL & Queries

### Q16: Write a query to find the top 5 stores by revenue

**Answer:**
```sql
SELECT TOP 5
    s.StoreId,
    s.StoreName,
    SUM(ih.TotalAmount) as Total_Revenue,
    COUNT(DISTINCT ih.InvoiceNo) as Transaction_Count,
    AVG(ih.TotalAmount) as Avg_Transaction
FROM Stores s
LEFT JOIN InvoiceHeaders ih ON s.StoreId = ih.StoreId
WHERE YEAR(ih.InvoiceDate) = 2019
GROUP BY s.StoreId, s.StoreName
ORDER BY Total_Revenue DESC
```

---

### Q17: How to calculate customer lifetime value (LTV)?

**Answer:**
```sql
SELECT 
    c.CustomerId,
    c.CustomerName,
    COUNT(DISTINCT ih.InvoiceNo) as Purchase_Count,
    SUM(ih.TotalAmount) as TotalLifetimeSpend,
    MIN(ih.InvoiceDate) as First_Purchase,
    MAX(ih.InvoiceDate) as Last_Purchase,
    DATEDIFF(DAY, MIN(ih.InvoiceDate), MAX(ih.InvoiceDate)) as Customer_Tenure_Days,
    CASE 
        WHEN SUM(ih.TotalAmount) > 50000 THEN 'High Value'
        WHEN SUM(ih.TotalAmount) > 20000 THEN 'Medium Value'
        ELSE 'Low Value'
    END as ValueSegment
FROM Customers c
LEFT JOIN InvoiceHeaders ih ON c.CustomerId = ih.CustomerID
GROUP BY c.CustomerId, c.CustomerName
ORDER BY TotalLifetimeSpend DESC
```

---

### Q18: How to create an RFM (Recency-Frequency-Monetary) segment?

**Answer:**
```sql
WITH customer_metrics AS (
    SELECT 
        c.CustomerId,
        c.CustomerName,
        DATEDIFF(DAY, MAX(ih.InvoiceDate), '2019-09-30') as Recency_Days,
        COUNT(DISTINCT ih.InvoiceNo) as Frequency,
        SUM(ih.TotalAmount) as Monetary
    FROM Customers c
    LEFT JOIN InvoiceHeaders ih ON c.CustomerId = ih.CustomerID
    GROUP BY c.CustomerId, c.CustomerName
),
rfm_scoring AS (
    SELECT 
        *,
        NTILE(5) OVER (ORDER BY Recency_Days DESC) as R_Score,
        NTILE(5) OVER (ORDER BY Frequency ASC) as F_Score,
        NTILE(5) OVER (ORDER BY Monetary ASC) as M_Score
    FROM customer_metrics
)
SELECT 
    *,
    CASE 
        WHEN R_Score = 5 AND F_Score >= 4 AND M_Score >= 4 THEN 'Champions'
        WHEN R_Score >= 4 AND F_Score >= 3 AND M_Score >= 3 THEN 'Loyal Customers'
        WHEN R_Score >= 4 AND F_Score >= 2 THEN 'Potential Loyalists'
        WHEN R_Score <= 2 AND F_Score >= 3 THEN 'At Risk'
        WHEN F_Score = 1 THEN 'Lost'
        ELSE 'Need Attention'
    END as RFM_Segment
FROM rfm_scoring
ORDER BY R_Score DESC, F_Score DESC, M_Score DESC
```

---

### Q19: How to detect product seasonality?

**Answer:**
```sql
WITH monthly_sales AS (
    SELECT 
        i.ItemId,
        i.ItemName,
        MONTH(ih.InvoiceDate) as SalesMonth,
        SUM(id.Quantity) as Monthly_Quantity,
        SUM(id.TotalPrice) as Monthly_Sales
    FROM InvoiceDetails id
    JOIN InvoiceHeaders ih ON id.InvoiceNo = ih.InvoiceNo
    JOIN Items i ON id.ItemId = i.ItemId
    GROUP BY i.ItemId, i.ItemName, MONTH(ih.InvoiceDate)
),
seasonality AS (
    SELECT 
        ItemId,
        ItemName,
        AVG(Monthly_Sales) as Avg_Monthly_Sales,
        STDDEV(Monthly_Sales) as Std_Dev_Sales,
        MAX(Monthly_Sales) / MIN(Monthly_Sales) as Seasonality_Index
    FROM monthly_sales
    GROUP BY ItemId, ItemName
)
SELECT * FROM seasonality
WHERE Seasonality_Index > 2.0  -- High seasonality
ORDER BY Seasonality_Index DESC
```

---

### Q20: How to find product pairs bought together (market basket)?

**Answer:**
```sql
WITH product_pairs AS (
    SELECT 
        id1.ItemId as Product1,
        id2.ItemId as Product2,
        COUNT(DISTINCT id1.InvoiceNo) as Co_Occurrences
    FROM InvoiceDetails id1
    JOIN InvoiceDetails id2 ON id1.InvoiceNo = id2.InvoiceNo
        AND id1.ItemId < id2.ItemId
    GROUP BY id1.ItemId, id2.ItemId
    HAVING COUNT(DISTINCT id1.InvoiceNo) >= 3
)
SELECT 
    i1.ItemName as Product1,
    i2.ItemName as Product2,
    pp.Co_Occurrences,
    CAST(100.0 * pp.Co_Occurrences / (SELECT COUNT(DISTINCT InvoiceNo) FROM InvoiceHeaders) as DECIMAL(5,2)) as Co_Purchase_Pct
FROM product_pairs pp
JOIN Items i1 ON pp.Product1 = i1.ItemId
JOIN Items i2 ON pp.Product2 = i2.ItemId
ORDER BY Co_Occurrences DESC
```

---

### Q21-Q30: Additional SQL Questions

(Abbreviated for space)

**Q21:** Window functions - calculate running total
**Q22:** CTEs (Common Table Expressions) - multi-step queries
**Q23:** Self-join - find customers from same city
**Q24:** LEFT JOIN vs INNER JOIN trade-offs
**Q25:** Query optimization - execution plans
**Q26:** Aggregate functions - GROUP BY edge cases
**Q27:** UNION vs UNION ALL performance
**Q28:** Subqueries vs JOINs - when to use each
**Q29:** Full-text search on product descriptions
**Q30:** Handling NULL values in aggregations

---

## Data Analytics

### Q31: How do you approach a new analytics project?

**Answer:**

**5-Step Framework:**

1. **Define the Question**
   - What decision does this support?
   - Who are the stakeholders?
   - What metrics matter?

2. **Gather Data**
   - Identify data sources
   - Assess data quality
   - Document assumptions

3. **Explore & Visualize**
   - Descriptive statistics (mean, median, std dev)
   - Identify outliers and anomalies
   - Create preliminary visualizations

4. **Analyze & Model**
   - Correlation analysis
   - Hypothesis testing
   - Predictive models

5. **Communicate & Act**
   - Create dashboards
   - Document findings
   - Recommend actions

---

### Q32: What is RFM segmentation and why use it?

**Answer:**

**RFM = Recency + Frequency + Monetary**

| Metric | Definition | Why | Example |
|--------|-----------|-----|---------|
| **Recency** | Days since last purchase | Recent buyers are more engaged | 7 days vs. 90 days |
| **Frequency** | Number of purchases | Loyalty indicator | 1 purchase vs. 10+ |
| **Monetary** | Total spend | Revenue indicator | $100 vs. $10,000 |

**7 Segments Generated:**
1. **Champions** (R5 F5 M5): Best customers, frequent, high spend
2. **Loyal Customers** (R4-5 F4-5 M4-5): Consistent, reliable
3. **Potential Loyalists** (R4-5 F2-3): Good potential
4. **At Risk** (R2-3 F2-3): Declining activity
5. **Cant Lose Them** (R1-2 F5 M5): Best revenue, but inactive
6. **Lost** (R1 F1 M1): Inactive, low value
7. **Need Attention** (R3 F3 M3): Middle of road

**Business Actions:**
- **Champions:** VIP programs, exclusive offers
- **At Risk:** Re-engagement campaigns
- **Lost:** Win-back offers
- **Potential Loyalists:** Nurture with discounts

---

### Q33: How to calculate churn risk?

**Answer:**

**Churn Risk Score:**

```python
def calculate_churn_risk(customer_data):
    # Recency (weight: 40%)
    recency_score = (customer_data['days_since_last_purchase'] / 90) * 100
    
    # Frequency (weight: 30%)
    frequency_score = (1 - customer_data['purchase_frequency'] / 10) * 100
    
    # Trend (weight: 30%)
    spending_trend = customer_data['avg_spending_last_30'] / customer_data['avg_spending_prev_90']
    trend_score = max(0, (1 - spending_trend) * 100)
    
    # Composite score
    churn_risk = (
        0.4 * recency_score +
        0.3 * frequency_score +
        0.3 * trend_score
    )
    
    # Categorize
    if churn_risk >= 75:
        return 'High Risk'
    elif churn_risk >= 50:
        return 'Medium Risk'
    else:
        return 'Low Risk'
```

**Interpretation:**
- High Risk (≥75): Inactive for 60+ days, declining spending
- Medium Risk (50-74): Mixed signals
- Low Risk (<50): Recent activity, stable spend

---

### Q34-Q50: Additional Analytics Questions

(Abbreviated)

**Q34:** Cohort analysis - track customer groups over time
**Q35:** Attribution modeling - which channel drives sales?
**Q36:** A/B testing - statistical significance in experiments
**Q37:** Correlation vs causation - common pitfalls
**Q38:** Outlier detection - anomalies in data
**Q39:** Dimensionality reduction - PCA, feature selection
**Q40:** Clustering - customer segmentation beyond RFM
**Q41:** Regression analysis - predicting continuous variables
**Q42:** Classification - binary and multi-class problems
**Q43:** Cross-validation - ensuring model generalization
**Q44:** Feature engineering - creating new variables
**Q45:** Data normalization - scaling for ML algorithms
**Q46:** Imbalanced datasets - handling skewed labels
**Q47:** Time-series decomposition - trend, seasonality, noise
**Q48:** Correlation matrix - finding relationships
**Q49:** Heatmaps - visualizing data patterns
**Q50:** Dashboard design - effective visualization principles

---

## Forecasting

### Q51: What are the 4 forecasting methods used?

**Answer:**

| Method | Approach | Forecast | When to Use |
|--------|----------|----------|-------------|
| **Bottom-Up** | Forecast lowest level → aggregate | $2.05M | Detailed planning |
| **Top-Down** | Forecast total → disaggregate | $3.13M | Executive reporting |
| **ARIMA** | Regression on lagged values | $2.40M | Non-seasonal data |
| **SARIMA** | ARIMA + seasonal component | ~$2.4M | Retail with seasonality |

---

### Q52: Explain Bottom-Up forecasting

**Answer:**

**Algorithm:**
```
1. Forecast at lowest level (Item per Store)
2. Aggregate to Department level (sum by department)
3. Aggregate to Store level (sum by store)
4. Aggregate to Company level (sum across all stores)
```

**Advantages:**
- Most accurate at detail level
- Captures item-specific patterns
- Enables drill-down analysis

**Disadvantages:**
- Error compounds at higher levels
- More computationally intensive
- Requires more data per item

**Python Implementation:**
```python
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def bottom_up_forecast(sales_data, periods=30):
    forecasts = {}
    
    # Group by Store-Item
    for (store, item), group_data in sales_data.groupby(['StoreId', 'ItemId']):
        # Forecast at detail level
        model = ExponentialSmoothing(group_data['Sales'], trend='add')
        forecast = model.fit().forecast(periods)
        forecasts[(store, item)] = forecast.sum()
    
    # Aggregate upward
    return pd.Series(forecasts).groupby(level=0).sum()
```

---

### Q53: Explain Top-Down forecasting

**Answer:**

**Algorithm:**
```
1. Forecast at company level (total sales)
2. Calculate proportion for each store (vs total)
3. Allocate store forecast using proportion
4. Further allocate by department
```

**Advantages:**
- Stable aggregate forecast
- Less error variance
- Faster computation

**Disadvantages:**
- Less detailed
- May miss item-specific patterns
- Requires historical proportions

**Python Implementation:**
```python
def top_down_forecast(sales_data, periods=30):
    # Forecast total
    total_series = sales_data.groupby('Date')['Sales'].sum()
    model = ExponentialSmoothing(total_series, trend='add')
    total_forecast = model.fit().forecast(periods)
    
    # Calculate store proportions
    store_pct = (sales_data.groupby('StoreId')['Sales'].sum() / 
                 sales_data['Sales'].sum())
    
    # Allocate forecast
    store_forecasts = {}
    for store_id, pct in store_pct.items():
        store_forecasts[store_id] = total_forecast * pct
    
    return pd.DataFrame(store_forecasts)
```

---

### Q54: Explain ARIMA forecasting

**Answer:**

**ARIMA = Auto-Regressive Integrated Moving Average**

- **AR (p):** Auto-regressive - depends on past values
- **I (d):** Integrated - differencing to make stationary
- **MA (q):** Moving average - depends on past errors

**Mathematical Model:**
```
y(t) = c + φ₁*y(t-1) + φ₂*y(t-2) + ... + εₜ + θ₁*εₜ₋₁ + ...
```

**Python Implementation:**
```python
from statsmodels.tsa.arima.model import ARIMA

def forecast_arima(sales_series, periods=30):
    # Auto-select parameters
    model = ARIMA(sales_series, order=(1, 1, 1))
    fitted_model = model.fit()
    
    # Generate forecast
    forecast = fitted_model.get_forecast(steps=periods)
    forecast_df = forecast.conf_int()
    forecast_df['mean'] = forecast.predicted_mean
    
    return forecast_df
```

---

### Q55: Explain SARIMA forecasting

**Answer:**

**SARIMA = ARIMA + Seasonal component**

- **Seasonal (P,D,Q,s):** Seasonal orders repeated at interval s
- **s = 12** for monthly seasonality (12 months)
- **s = 7** for weekly seasonality (7 days)

**Model:**
```
SARIMA(p,d,q)(P,D,Q)₁₂
Combines:
- Regular differencing (d)
- Seasonal differencing (D)
- AR/MA terms at lag 1
- Seasonal AR/MA terms at lag 12
```

**Python Implementation:**
```python
from statsmodels.tsa.statespace.sarimax import SARIMAX

def forecast_sarima(sales_series, periods=30):
    # SARIMA(1,1,1)(1,1,1,12) for monthly seasonality
    model = SARIMAX(
        sales_series,
        order=(1, 1, 1),
        seasonal_order=(1, 1, 1, 12)
    )
    fitted_model = model.fit()
    
    forecast = fitted_model.get_forecast(steps=periods)
    return forecast.summary_frame()
```

---

### Q56: How to evaluate forecast accuracy?

**Answer:**

**Metrics:**

```
MAE (Mean Absolute Error):
MAE = Σ|yₜ - ŷₜ| / n
- Interpretation: Average absolute deviation
- Units: Same as y (dollars, units)

RMSE (Root Mean Squared Error):
RMSE = √(Σ(yₜ - ŷₜ)² / n)
- Interpretation: Penalizes large errors
- Units: Same as y

MAPE (Mean Absolute Percentage Error):
MAPE = Σ|yₜ - ŷₜ|/|yₜ| / n * 100
- Interpretation: % error (scale-independent)
- Range: 0% (perfect) to 100%+
- Ideal: MAPE < 10%
```

**SQL Query:**
```sql
SELECT 
    AVG(ABS(ForecastedAmount - ActualAmount)) as MAE,
    SQRT(AVG(POWER(ForecastedAmount - ActualAmount, 2))) as RMSE,
    AVG(ABS((ForecastedAmount - ActualAmount) / ActualAmount)) * 100 as MAPE_Pct
FROM ForecastValidation
WHERE ActualAmount > 0
```

---

### Q57-Q65: Additional Forecasting Questions

(Abbreviated)

**Q57:** Time-series stationarity - why it matters, how to achieve
**Q58:** ACF/PACF plots - identifying AR/MA orders
**Q59:** Seasonal decomposition - extracting components
**Q60:** Exponential smoothing - simple, Holt, Holt-Winters
**Q61:** Prophet - Facebook's forecasting library features
**Q62:** Ensemble methods - combining multiple forecasts
**Q63:** Forecast bias - systematic over/under prediction
**Q64:** Confidence intervals - quantifying uncertainty
**Q65:** Back-testing - evaluating historical accuracy

---

## Security & RLS

### Q66: What is Row-Level Security (RLS)?

**Answer:**

**Definition:** 
Filter database query results based on user identity and permissions.

**Example:**
- Store Manager (Sarah) sees only Store #5 data
- Regional Manager (John) sees Stores #1-10 data
- CEO (Jane) sees all data

**Architecture:**

```
User Login
    ↓
Authenticate via AD/Database
    ↓
Lookup SecurityUsers table
    ↓
Get user role (Store Manager, Regional Manager, etc.)
    ↓
Query UserStoreAccess mapping
    ↓
Build WHERE clause: WHERE StoreId IN (5)
    ↓
Execute filtered query
    ↓
Log access in AuditLog
```

---

### Q67: How to implement RLS in SQL Server?

**Answer:**

**Step 1: Create Security Tables**

```sql
CREATE TABLE SecurityUsers (
    UserId INT PRIMARY KEY,
    UserName NVARCHAR(50),
    Email NVARCHAR(100),
    RoleId INT,
    CreatedDate DATETIME DEFAULT GETDATE()
)

CREATE TABLE SecurityRoles (
    RoleId INT PRIMARY KEY,
    RoleName NVARCHAR(50),
    Permissions NVARCHAR(MAX)  -- JSON format
)

CREATE TABLE UserStoreAccess (
    UserId INT,
    StoreId INT,
    AccessLevel NVARCHAR(20),  -- View, Edit, Admin
    PRIMARY KEY (UserId, StoreId),
    FOREIGN KEY (UserId) REFERENCES SecurityUsers(UserId),
    FOREIGN KEY (StoreId) REFERENCES Stores(StoreId)
)

CREATE TABLE AuditLog (
    LogId INT IDENTITY PRIMARY KEY,
    UserId INT,
    QueryText NVARCHAR(MAX),
    DataAccessed NVARCHAR(500),
    Timestamp DATETIME DEFAULT GETDATE()
)
```

**Step 2: Create Security Predicate**

```sql
CREATE FUNCTION fn_StoreAccessPredicate(@StoreId INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN 
    SELECT 1 AS AccessPredicate
    WHERE @StoreId IN (
        SELECT StoreId 
        FROM UserStoreAccess 
        WHERE UserId = SESSION_CONTEXT(N'UserId')
    ) 
    OR IS_ROLEMEMBER('Admin') = 1  -- Admins see all
```

**Step 3: Apply RLS Policy**

```sql
CREATE SECURITY POLICY store_security_policy
ADD FILTER PREDICATE fn_StoreAccessPredicate(StoreId) 
    ON dbo.InvoiceHeaders,
ADD BLOCK PREDICATE fn_StoreAccessPredicate(StoreId) 
    ON dbo.InvoiceHeaders AFTER INSERT

ENABLE ALTER DATABASE SCOPED CONFIGURATION 
ENABLE BLOCK_EXTERNAL_ACCESS_PRED ON
```

**Step 4: Set User Context**

```python
# In Python before querying
EXEC sp_set_session_context @key=N'UserId', @value=5

# Now queries are filtered automatically
SELECT * FROM InvoiceHeaders  
-- Only returns data for stores user 5 has access to
```

---

### Q68: How to audit data access?

**Answer:**

**Logging Strategy:**

```sql
CREATE TRIGGER tr_AuditInvoiceAccess ON InvoiceHeaders
AFTER SELECT
AS
BEGIN
    INSERT INTO AuditLog (UserId, QueryText, DataAccessed, Timestamp)
    VALUES (
        SESSION_CONTEXT(N'UserId'),
        @@PROCID,  -- Procedure ID
        'InvoiceHeaders SELECT',
        GETDATE()
    )
END

CREATE TRIGGER tr_AuditInvoiceUpdate ON InvoiceHeaders
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    INSERT INTO AuditLog (UserId, QueryText, DataAccessed, Timestamp)
    SELECT 
        SESSION_CONTEXT(N'UserId'),
        'UPDATE/DELETE ' + OBJECT_NAME(@@PROCID),
        'Modified ' + CAST(@@ROWCOUNT as VARCHAR),
        GETDATE()
END
```

**Audit Dashboard Query:**

```sql
SELECT 
    u.UserName,
    r.RoleName,
    al.DataAccessed,
    COUNT(*) as AccessCount,
    MAX(al.Timestamp) as LastAccess
FROM AuditLog al
JOIN SecurityUsers u ON al.UserId = u.UserId
LEFT JOIN SecurityRoles r ON u.RoleId = r.RoleId
WHERE al.Timestamp >= DATEADD(DAY, -30, GETDATE())
GROUP BY u.UserName, r.RoleName, al.DataAccessed
ORDER BY AccessCount DESC
```

---

### Q69: How to support 700+ users?

**Answer:**

**Scalability Approach:**

1. **Connection Pooling**
   ```
   10-100 pooled connections (not 700 individual)
   Reuse connections across requests
   Reduces memory & CPU overhead
   ```

2. **Caching Layer**
   ```
   Cache user permissions (1 hour TTL)
   Cache store access mappings
   Reduces RLS predicate evaluation
   ```

3. **Read Replicas**
   ```
   Primary: Transactional writes
   Replica1, Replica2, ...: Read-only queries
   Load balance across replicas
   ```

4. **Query Optimization**
   ```sql
   -- Create indexed view for filtered data
   CREATE VIEW v_UserInvoices
   WITH SCHEMABINDING
   AS
   SELECT i.* FROM InvoiceHeaders i
   WHERE i.StoreId IN (
       SELECT StoreId FROM UserStoreAccess 
       WHERE UserId = SESSION_CONTEXT(N'UserId')
   )
   
   CREATE CLUSTERED INDEX idx_user_invoices ON v_UserInvoices(StoreId, InvoiceDate)
   ```

5. **Monitoring**
   ```sql
   -- Monitor active connections
   SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE database_id = DB_ID()
   
   -- Identify slow queries
   SELECT * FROM sys.dm_exec_query_stats 
   ORDER BY total_elapsed_time DESC
   ```

---

### Q70-Q80: Additional Security Questions

(Abbreviated)

**Q70:** Azure AD integration - OAuth, SAML
**Q71:** Encryption - TDE, transparent data encryption
**Q72:** Database-level encryption vs column-level
**Q73:** Backup and disaster recovery - RPO/RTO
**Q74:** Role-based access control (RBAC)
**Q75:** API authentication - JWT tokens
**Q76:** SQL injection prevention - parameterized queries
**Q77:** Data masking - PII protection
**Q78:** Compliance - GDPR, HIPAA, SOC2
**Q79:** Penetration testing - security assessment
**Q80:** Incident response - breach detection

---

## Python & Development

### Q81: How to structure a Python analytics project?

**Answer:**

**Directory Structure:**

```
walmart-analytics/
├── src/
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── dashboard.py          # Main Streamlit app
│   │   ├── analytics_queries.py   # SQL queries
│   │   └── hierarchical_forecasting.py  # Forecasting models
│   └── config/
│       ├── __init__.py
│       └── settings.py            # Configuration
├── database/
│   ├── WALMART_SQL_QUERIES.sql
│   ├── RLS_DOCUMENTATION.sql
│   └── setup_dims_facts.py
├── tests/
│   ├── test_forecasting.py
│   ├── test_queries.py
│   └── test_analytics.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── QUERIES.md
│   └── INTERVIEW_ANSWERS.md
├── .gitignore
├── requirements.txt
└── README.md
```

**Best Practices:**
- Separate concerns (analytics, config, database)
- Single responsibility principle per file
- DRY (Don't Repeat Yourself)
- Clear naming conventions
- Comprehensive documentation

---

### Q82: How to handle database connections?

**Answer:**

**Connection Pooling:**

```python
import pyodbc
from contextlib import contextmanager

class DatabaseConnector:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.pool = None
    
    def create_pool(self):
        self.pool = pyodbc.pool.SimpleConnectionPool(
            minconn=5,
            maxconn=20,
            dsn=self.connection_string
        )
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

# Usage
db = DatabaseConnector('WalmartAnalytics')
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
```

---

### Q83: How to implement error handling?

**Answer:**

```python
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def handle_database_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pyodbc.DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise
        except pyodbc.ProgrammingError as e:
            logger.error(f"SQL error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    return wrapper

@handle_database_error
def query_invoices():
    conn = get_connection()
    cursor = conn.cursor()
    return cursor.execute("SELECT * FROM InvoiceHeaders").fetchall()
```

---

### Q84: How to optimize Streamlit performance?

**Answer:**

```python
import streamlit as st
import pandas as pd

# 1. Cache data (30-minute TTL)
@st.cache_data(ttl=1800)
def load_store_data():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM Stores", conn)

# 2. Cache expensive computations
@st.cache_resource
def get_forecast_model():
    from statsmodels.tsa.arima.model import ARIMA
    data = load_sales_data()
    return ARIMA(data, order=(1, 1, 1))

# 3. Use selectbox/slider for filtering (not refresh entire page)
store_id = st.selectbox("Select Store", load_store_data()['StoreId'])
data = load_store_data().query(f"StoreId == {store_id}")

# 4. Lazy load heavy visualizations
if st.checkbox("Show Advanced Analysis"):
    run_expensive_forecast()

# 5. Use session state to track user interactions
if 'forecast_cache' not in st.session_state:
    st.session_state.forecast_cache = {}
```

---

### Q85: How to test Python code?

**Answer:**

```python
import pytest
from unittest.mock import patch, MagicMock
from src.analytics.hierarchical_forecasting import bottomup_forecast

class TestForecasting:
    
    def test_bottomup_forecast_returns_dataframe(self):
        """Test that bottom-up forecast returns DataFrame"""
        mock_data = pd.DataFrame({
            'Date': pd.date_range('2019-07-01', periods=90),
            'Sales': [1000, 1100, 900] * 30,
            'StoreId': [1] * 90,
            'ItemId': [1] * 90
        })
        
        result = bottomup_forecast(mock_data, periods=30)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 30
        assert 'StoreId' in result.columns
    
    @patch('src.analytics.hierarchical_forecasting.ExponentialSmoothing')
    def test_forecast_handles_missing_data(self, mock_model):
        """Test forecast handles missing data gracefully"""
        mock_data = pd.DataFrame({
            'Date': ['2019-07-01', None, '2019-07-03'],
            'Sales': [1000, 1100, None]
        })
        
        with pytest.raises(ValueError):
            bottomup_forecast(mock_data)
    
    def test_forecast_values_positive(self):
        """Test that forecast values are positive"""
        mock_data = generate_test_data()
        result = bottomup_forecast(mock_data, periods=30)
        
        assert (result['forecast'] > 0).all(), "Forecasts should be positive"

# Run tests
# pytest tests/test_forecasting.py -v
```

---

### Q86: How to document code?

**Answer:**

```python
"""
Module: hierarchical_forecasting

This module implements four hierarchical forecasting methods:
- Bottom-Up: Forecast lowest level, aggregate upward
- Top-Down: Forecast total, disaggregate downward
- ARIMA: Auto-regressive integrated moving average
- SARIMA: ARIMA with seasonal components

Example:
    >>> from hierarchical_forecasting import bottomup_forecast
    >>> forecast = bottomup_forecast(sales_data, periods=30)
    >>> forecast.head()
"""

def bottomup_forecast(sales_data: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """
    Generate bottom-up hierarchical forecast.
    
    Forecasts at the lowest level (Store-Item), then aggregates
    upward to Department and Store levels.
    
    Args:
        sales_data (pd.DataFrame): Input time series with columns:
            - Date: Transaction date
            - Sales: Daily sales amount
            - StoreId: Store identifier
            - ItemId: Item identifier
        periods (int): Number of periods to forecast (default: 30)
    
    Returns:
        pd.DataFrame: Forecasts with columns:
            - StoreId: Store identifier
            - ItemId: Item identifier
            - Forecast: Predicted sales for each period
            - Upper_CI: 95% confidence interval upper bound
            - Lower_CI: 95% confidence interval lower bound
    
    Raises:
        ValueError: If sales_data is empty or has missing required columns
        
    Example:
        >>> sales = pd.read_csv('sales.csv')
        >>> forecast = bottomup_forecast(sales, periods=30)
        >>> forecast.to_csv('forecast.csv', index=False)
    
    Notes:
        - Data should cover at least 30 periods for model stability
        - High volatility items may have wider confidence intervals
        - Seasonal patterns are not explicitly modeled (use SARIMA for seasonality)
    """
    if sales_data.empty:
        raise ValueError("sales_data cannot be empty")
    
    required_cols = {'Date', 'Sales', 'StoreId', 'ItemId'}
    if not required_cols.issubset(sales_data.columns):
        raise ValueError(f"Missing required columns: {required_cols - set(sales_data.columns)}")
    
    # Implementation...
    return forecasts
```

---

### Q87-Q100: Additional Development Questions

(Abbreviated)

**Q87:** Version control - Git best practices, branching strategy
**Q88:** CI/CD pipelines - GitHub Actions, Azure DevOps
**Q89:** Logging - structured logging, log levels
**Q90:** Configuration management - environment variables, secrets
**Q91:** API development - REST principles, FastAPI
**Q92:** Asynchronous programming - async/await, concurrency
**Q93:** Container deployment - Docker, Kubernetes basics
**Q94:** Monitoring - application metrics, alerting
**Q95:** Code review - peer feedback, quality standards
**Q96:** Refactoring - code smell detection, improvement
**Q97:** Technical debt - managing complexity, long-term sustainability
**Q98:** Performance profiling - bottleneck identification
**Q99:** Security in development - OWASP top 10
**Q100:** Career development - continuous learning, industry trends

---

## Summary

This document provides comprehensive technical coverage of:

✅ **Database Design** - Star schema, RLS, scalability (Q1-Q15)
✅ **SQL & Queries** - 10 production queries, advanced techniques (Q16-Q30)
✅ **Data Analytics** - RFM, churn, cohort analysis (Q31-Q50)
✅ **Forecasting** - 4 methods, accuracy metrics, evaluation (Q51-Q65)
✅ **Security** - RLS implementation, auditing, 700+ users (Q66-Q80)
✅ **Python Development** - Best practices, testing, documentation (Q81-Q100)

**Preparation Guide:**
1. Understand the database schema completely
2. Be ready to write SQL queries (CTEs, window functions, aggregations)
3. Know the 4 forecasting methods and trade-offs
4. Understand RLS architecture and scalability
5. Be familiar with Python best practices and error handling

**Interview Tips:**
- Draw diagrams (schema, architecture, data flow)
- Explain trade-offs (Bottom-Up vs Top-Down, etc.)
- Give concrete examples from your project
- Show understanding of business impact
- Ask clarifying questions
- Share lessons learned

Good luck! 🎯
