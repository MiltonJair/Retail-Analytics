-- ============================================================================
-- WALMART ANALYTICS - SETUP DATABASE
-- Archivo ÚNICO para crear y poblar la BD
-- ============================================================================
-- Ejecutar: python database/run_setup.py

DROP DATABASE IF EXISTS WalmartAnalytics;
GO

CREATE DATABASE WalmartAnalytics;
GO

USE WalmartAnalytics;
GO

-- ============================================================================
-- CREAR TABLAS
-- ============================================================================

CREATE TABLE dbo.Stores (
    StoreID INT PRIMARY KEY,
    StoreName NVARCHAR(100) NOT NULL,
    Address NVARCHAR(200),
    City NVARCHAR(50),
    State NVARCHAR(2),
    PostalCode NVARCHAR(10),
    ManagerName NVARCHAR(100)
);

CREATE TABLE dbo.Departments (
    DepartmentID INT PRIMARY KEY IDENTITY(1,1),
    DepartmentName NVARCHAR(50) NOT NULL UNIQUE,
    Description NVARCHAR(500)
);

CREATE TABLE dbo.Items (
    ItemID INT PRIMARY KEY IDENTITY(1,1),
    ItemCode NVARCHAR(20) NOT NULL UNIQUE,
    ItemName NVARCHAR(100) NOT NULL,
    DepartmentID INT NOT NULL REFERENCES dbo.Departments(DepartmentID),
    UnitPrice DECIMAL(10, 2) NOT NULL
);

CREATE TABLE dbo.InvoiceHeaders (
    InvoiceID INT PRIMARY KEY IDENTITY(1,1),
    InvoiceNumber NVARCHAR(30) NOT NULL UNIQUE,
    StoreID INT NOT NULL REFERENCES dbo.Stores(StoreID),
    InvoiceDate DATETIME NOT NULL,
    TotalAmount DECIMAL(12, 2),
    TotalItems INT,
    CashierName NVARCHAR(100),
    CustomerID INT NULL
);

CREATE TABLE dbo.InvoiceDetails (
    DetailID INT PRIMARY KEY IDENTITY(1,1),
    InvoiceID INT NOT NULL REFERENCES dbo.InvoiceHeaders(InvoiceID),
    ItemID INT NOT NULL REFERENCES dbo.Items(ItemID),
    QuantitySold INT NOT NULL,
    UnitPrice DECIMAL(10, 2) NOT NULL,
    LineTotal DECIMAL(12, 2)
);

CREATE TABLE dbo.Customers (
    CustomerID INT PRIMARY KEY IDENTITY(1,1),
    CustomerCode NVARCHAR(20) NOT NULL UNIQUE,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100),
    Phone NVARCHAR(15),
    City NVARCHAR(50),
    State NVARCHAR(2),
    JoinDate DATETIME NOT NULL,
    LoyaltyMember BIT DEFAULT 0,
    MembershipTier NVARCHAR(20),
    LastPurchaseDate DATETIME,
    TotalLifetimeSpend DECIMAL(12,2) DEFAULT 0
);

CREATE TABLE dbo.CustomerRFM (
    CustomerID INT PRIMARY KEY,
    Recency INT,
    Frequency INT,
    Monetary DECIMAL(12,2),
    R_Score INT,
    F_Score INT,
    M_Score INT,
    RFM_Score NVARCHAR(10),
    Segment NVARCHAR(30),
    LastCalculatedDate DATETIME,
    FOREIGN KEY (CustomerID) REFERENCES dbo.Customers(CustomerID)
);

CREATE TABLE dbo.CustomerChurnRisk (
    CustomerID INT PRIMARY KEY,
    DaysSinceLastPurchase INT,
    PurchaseFrequency INT,
    AverageTicket DECIMAL(10,2),
    MonthlySpendTrend NVARCHAR(10),
    VisitFrequency INT,
    DepartmentDiversity INT,
    ChurnRiskScore DECIMAL(5,2),
    ChurnRiskCategory NVARCHAR(20),
    RecommendedAction NVARCHAR(100),
    PredictionDate DATETIME,
    FOREIGN KEY (CustomerID) REFERENCES dbo.Customers(CustomerID)
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

CREATE NONCLUSTERED INDEX idx_InvoiceHeaders_Date ON dbo.InvoiceHeaders(InvoiceDate);
CREATE NONCLUSTERED INDEX idx_InvoiceHeaders_Store ON dbo.InvoiceHeaders(StoreID);
CREATE NONCLUSTERED INDEX idx_InvoiceDetails_Invoice ON dbo.InvoiceDetails(InvoiceID);
CREATE NONCLUSTERED INDEX idx_Items_Department ON dbo.Items(DepartmentID);
CREATE NONCLUSTERED INDEX idx_Customers_State ON dbo.Customers(State);
CREATE NONCLUSTERED INDEX idx_Customers_JoinDate ON dbo.Customers(JoinDate);

-- ============================================================================
-- INSERT STORES
-- ============================================================================

INSERT INTO dbo.Stores VALUES 
(1, 'Store 1 NY', '100 Main St', 'New York', 'NY', '10001', 'Manager A'),
(2, 'Store 2 CA', '200 Market St', 'San Francisco', 'CA', '94102', 'Manager B'),
(3, 'Store 3 TX', '300 Oak Ave', 'Houston', 'TX', '77001', 'Manager C'),
(4, 'Store 4 FL', '400 Beach Rd', 'Miami', 'FL', '33101', 'Manager D'),
(5, 'Store 5 WA', '500 Pine St', 'Seattle', 'WA', '98101', 'Manager E'),
(6, 'Store 6 IL', '600 State St', 'Chicago', 'IL', '60601', 'Manager F'),
(7, 'Store 7 PA', '700 Liberty Ave', 'Pittsburgh', 'PA', '15222', 'Manager G'),
(8, 'Store 8 MA', '800 Newbury St', 'Boston', 'MA', '02116', 'Manager H'),
(9, 'Store 9 AZ', '900 Central Ave', 'Phoenix', 'AZ', '85001', 'Manager I'),
(10, 'Store 10 CO', '1000 16th St', 'Denver', 'CO', '80202', 'Manager J'),
(11, 'Store 11 GA', '1100 Peachtree St', 'Atlanta', 'GA', '30309', 'Manager K'),
(12, 'Store 12 NC', '1200 Fayetteville St', 'Raleigh', 'NC', '27601', 'Manager L'),
(13, 'Store 13 MN', '1300 Nicollet Ave', 'Minneapolis', 'MN', '55401', 'Manager M'),
(14, 'Store 14 TN', '1400 Broadway', 'Nashville', 'TN', '37201', 'Manager N'),
(15, 'Store 15 OH', '1500 Public Square', 'Cleveland', 'OH', '44114', 'Manager O'),
(16, 'Store 16 MI', '1600 Woodward Ave', 'Detroit', 'MI', '48226', 'Manager P'),
(17, 'Store 17 IN', '1700 Monument Cir', 'Indianapolis', 'IN', '46204', 'Manager Q'),
(18, 'Store 18 VA', '1800 Main St', 'Richmond', 'VA', '23219', 'Manager R'),
(19, 'Store 19 WI', '1900 Wisconsin Ave', 'Milwaukee', 'WI', '53201', 'Manager S'),
(20, 'Store 20 MO', '2000 Market St', 'St. Louis', 'MO', '63101', 'Manager T');

-- ============================================================================
-- INSERT DEPARTMENTS & ITEMS
-- ============================================================================

INSERT INTO dbo.Departments (DepartmentName, Description) VALUES
('Clothing', 'Apparel and accessories'),
('Home', 'Home and kitchen'),
('Sports', 'Sports and outdoors'),
('Food', 'Groceries and beverages'),
('Health', 'Health and beauty'),
('Toys', 'Toys and games'),
('Electronics', 'Electronics and gadgets');

INSERT INTO dbo.Items (ItemCode, ItemName, DepartmentID, UnitPrice) VALUES
('CLT001', 'T-Shirt', 1, 19.99),
('CLT002', 'Jeans', 1, 49.99),
('CLT003', 'Jacket', 1, 89.99),
('CLT004', 'Shoes', 1, 59.99),
('HOM001', 'Pillow', 2, 29.99),
('HOM002', 'Bedsheet', 2, 39.99),
('HOM003', 'Towel', 2, 14.99),
('SPT001', 'Basketball', 3, 24.99),
('SPT002', 'Yoga Mat', 3, 34.99),
('SPT003', 'Bicycle', 3, 199.99),
('FOD001', 'Cereal', 4, 4.99),
('FOD002', 'Milk', 4, 3.99),
('FOD003', 'Bread', 4, 2.99),
('FOD004', 'Coffee', 4, 9.99),
('HEA001', 'Shampoo', 5, 7.99),
('HEA002', 'Toothbrush', 5, 3.99),
('HEA003', 'Sunscreen', 5, 12.99),
('TOY001', 'Lego Set', 6, 49.99),
('TOY002', 'Board Game', 6, 19.99),
('TOY003', 'Action Figure', 6, 14.99),
('ELC001', 'Headphones', 7, 79.99),
('ELC002', 'Phone Case', 7, 19.99),
('ELC003', 'USB Cable', 7, 9.99),
('ELC004', 'Power Bank', 7, 29.99),
('ELC005', 'Laptop Stand', 7, 39.99),
('ELC006', 'Monitor', 7, 299.99);

-- ============================================================================
-- INSERT SYNTHETIC SALES DATA (90 días)
-- ============================================================================

DECLARE @StartDate DATETIME = '2019-07-01';
DECLARE @EndDate DATETIME = '2019-09-28';
DECLARE @CurrentDate DATETIME = @StartDate;
DECLARE @InvoiceID INT = 1;
DECLARE @StoreID INT;
DECLARE @ItemID INT;
DECLARE @Quantity INT;

WHILE @CurrentDate <= @EndDate
BEGIN
    SET @StoreID = (CAST(RAND() * 19 AS INT) + 1);
    SET @Quantity = CAST(RAND() * 5 AS INT) + 1;
    SET @ItemID = (CAST(RAND() * 25 AS INT) + 1);
    
    INSERT INTO dbo.InvoiceHeaders (InvoiceNumber, StoreID, InvoiceDate, TotalAmount, TotalItems, CashierName, CustomerID)
    VALUES ('INV' + FORMAT(@InvoiceID, '000000'), @StoreID, @CurrentDate, 0, @Quantity, 'Cashier', NULL);
    
    INSERT INTO dbo.InvoiceDetails (InvoiceID, ItemID, QuantitySold, UnitPrice, LineTotal)
    SELECT @InvoiceID, @ItemID, @Quantity, UnitPrice, @Quantity * UnitPrice 
    FROM dbo.Items WHERE ItemID = @ItemID;
    
    SET @InvoiceID = @InvoiceID + 1;
    SET @CurrentDate = DATEADD(DAY, 1, @CurrentDate);
END;

GO

PRINT 'Database created successfully!';
