# Walmart Analytics - System Architecture

## Overview
Enterprise-grade analytics platform for hierarchical sales forecasting, customer segmentation, and row-level security with 700+ user support.

## Technology Stack

### Backend
- **Database:** SQL Server 2019 LocalDB (WalmartAnalytics)
- **Python:** 3.11
- **Web Framework:** Streamlit (http://localhost:8501)
- **Data Processing:** pandas, numpy, pyodbc

### Forecasting
- **Prophet:** Facebook's time-series forecasting library
- **ARIMA/SARIMA:** Statsmodels for seasonal decomposition
- **Hierarchical Methods:** Bottom-Up & Top-Down aggregations

### Data Visualization
- **Plotly:** Interactive charts and dashboards
- **Streamlit:** Web UI and session management

## System Architecture

```
┌─────────────────────────────────────────┐
│     Streamlit Dashboard (10 Views)      │
│  - Real-time analytics and forecasting  │
│  - Interactive RFM segmentation         │
│  - Customer churn analysis              │
└──────────┬──────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│   Analytics Layer (Python)              │
│  - Hierarchical forecasting (4 methods) │
│  - Customer RFM calculation (7 segments)│
│  - Churn risk scoring (3 categories)    │
│  - Data transformation & aggregation    │
└──────────┬──────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│   SQL Server 2019 LocalDB               │
│  ┌─────────────────────────────────────┐│
│  │ Core Tables                          ││
│  │ - Stores (20)                        ││
│  │ - Departments (7)                    ││
│  │ - Items (26)                         ││
│  │ - Invoices (10,619+)                 ││
│  │ - Customers (47)                     ││
│  ├─────────────────────────────────────┤│
│  │ Analytics Tables                     ││
│  │ - CustomerRFM (7 segments)           ││
│  │ - CustomerChurnRisk (3 categories)   ││
│  │ - SecurityUsers, SecurityRoles       ││
│  │ - UserStoreAccess, AuditLog          ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

## Data Flow

### 1. Data Ingestion
- Import from CSV or database dumps
- Validate data quality (see WALMART_SQL_QUERIES.sql Query 10)
- Stage into raw tables

### 2. Analytics Processing
```python
# Hierarchical Forecasting
1. Bottom-Up: Store → Department → Item level
2. Top-Down: Company → Store breakdown
3. ARIMA: Auto-regressive integrated moving average
4. SARIMA: Seasonal ARIMA with monthly patterns
```

### 3. Customer Analytics
```
Customer Transactions
        ↓
Calculate RFM Metrics:
  - Recency: Days since last purchase
  - Frequency: Number of purchases
  - Monetary: Total lifetime spend
        ↓
Assign RFM Segment (1-7):
  1. Champions (active, high spend)
  2. Loyal Customers (consistent)
  3. Potential Loyalists (growing)
  4. At Risk (declining activity)
  5. Cant Lose Them (high historical value)
  6. Lost (no recent activity)
  7. Need Attention (inactive)
        ↓
Calculate Churn Risk:
  - Low: Recent purchases (score < 50)
  - Medium: Some inactivity (score 50-74)
  - High: Significant inactivity (score ≥ 75)
```

### 4. Security (RLS)
```
User Login
  ↓
Check SecurityUsers table
  ↓
Retrieve UserStoreAccess mapping
  ↓
Apply RLS filters to queries
  ↓
Log access in AuditLog
  ↓
Return filtered results
```

## Forecasting Methods Comparison

### 1. Bottom-Up (Hierarchical)
- **Logic:** Forecast at lowest level (item per store) → aggregate upward
- **Accuracy:** Highest at item level, variance compounds upward
- **Forecast:** $2.05M (30-day)
- **Best For:** Store-specific inventory planning

### 2. Top-Down (Hierarchical)
- **Logic:** Forecast company total → disaggregate to stores/departments
- **Accuracy:** More stable aggregate forecasts
- **Forecast:** $3.13M (30-day)
- **Best For:** Executive reporting, resource allocation

### 3. ARIMA (Auto-Regressive)
- **Logic:** Linear model based on past values and residuals
- **Accuracy:** Good for non-seasonal trends
- **Forecast:** $2.40M (30-day)
- **Best For:** Fast forecasting, non-seasonal data

### 4. SARIMA (Seasonal ARIMA)
- **Logic:** ARIMA with seasonal components (monthly patterns)
- **Accuracy:** Captures recurring patterns (e.g., month-end spikes)
- **Forecast:** ~$2.4M (30-day)
- **Best For:** Retail data with strong seasonal patterns

## RLS (Row-Level Security) Architecture

### Components

1. **SecurityUsers Table**
   ```sql
   UserId, UserName, Email, Role, ReportingManager
   ```

2. **SecurityRoles Table**
   ```sql
   RoleId, RoleName, Permissions (JSON)
   ```

3. **UserStoreAccess Table**
   ```sql
   UserId, StoreId, AccessLevel (View/Edit/Admin)
   ```

4. **AuditLog Table**
   ```sql
   UserId, Query, DataAccessed, Timestamp
   ```

### Example: Store Manager Access
- **User:** Sarah (Store Manager at Store #5)
- **Login:** sarah@walmart.com
- **Role:** Store Manager
- **Access:** Only sees Store #5 data
- **Audit:** All queries logged with timestamp

### Scalability
- Supports 700+ concurrent users
- Efficient indexing on UserId, StoreId
- Materialized views for performance
- Partitioning by StoreId for large tables

## Data Quality Metrics

### Current Dataset
- **Time Period:** July - September 2019 (90 days)
- **Stores:** 20
- **Departments:** 7
- **Products (Items):** 26
- **Transactions:** 10,619+
- **Customers:** 47 active
- **Customer LTV Average:** $57,156

### Validation Queries (See WALMART_SQL_QUERIES.sql)
```sql
-- Query 10: Data Quality Metrics
- Transaction volume by store/department
- Customer distribution and segmentation
- Seasonal patterns and anomalies
- Missing or duplicate records
- Date range coverage verification
```

## Performance Optimization

### Database Level
- Composite indexes on (StoreId, Date)
- Materialized views for hierarchical aggregations
- Partitioning by StoreId for large tables
- Query optimization with execution plans

### Application Level
- Caching with Streamlit `@st.cache_data`
- Lazy loading of datasets
- Pre-calculated aggregations
- Connection pooling with pyodbc

### Expected Performance
- Dashboard load time: < 5 seconds
- Query execution: < 2 seconds
- Forecast generation: ~10-30 seconds per method

## Error Handling

### Database Errors
```python
try:
    cursor.execute(query)
except pyodbc.DatabaseError as e:
    st.error(f"Database error: {e}")
    log_error(e)
```

### Forecast Errors
```python
try:
    forecast = model.fit()
except Exception as e:
    st.warning(f"Forecast failed: {e}")
    use_fallback_method()
```

### Data Validation
```python
# Check for null values, outliers, duplicates
validate_data(df)
remove_outliers(df)
handle_missing_values(df)
```

## Deployment

### Local Development
```bash
pip install -r requirements.txt
streamlit run src/analytics/dashboard.py
```

### Production (Streamlit Cloud)
1. Push to GitHub repository
2. Connect Streamlit Cloud
3. Configure environment variables (.env)
4. Deploy with automatic CI/CD

### Enterprise Deployment (Azure)
1. SQL Server in Azure SQL Database
2. Python app in Azure Container Instances
3. Streamlit app in App Service
4. Azure AD for authentication
5. Azure Monitor for logging/alerting

## Future Enhancements

### Short-term (1-2 months)
- [ ] Real-time data pipeline with Apache Airflow
- [ ] Machine learning model tuning
- [ ] Mobile dashboard (Streamlit Mobile)
- [ ] Email alerts for anomalies

### Medium-term (3-6 months)
- [ ] Predictive inventory optimization
- [ ] Recommendation engine
- [ ] Advanced cohort analysis
- [ ] A/B testing framework

### Long-term (6-12 months)
- [ ] Full AI/ML pipeline
- [ ] Automated root-cause analysis
- [ ] Computer vision for retail analytics
- [ ] Blockchain for supply chain tracking

## References
- See QUERIES.md for detailed SQL query documentation
- See INTERVIEW_ANSWERS.md for technical Q&A
- See README.md for quick start and feature overview
