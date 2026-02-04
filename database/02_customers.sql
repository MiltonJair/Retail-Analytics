-- ============================================================================
-- WALMART ANALYTICS - CUSTOMERS & ADVANCED ANALYTICS
-- Archivo ÚNICO para clientes, RFM y Churn prediction
-- ============================================================================

USE WalmartAnalytics;
GO

-- ============================================================================
-- POPULATE CUSTOMERS (500)
-- ============================================================================

DECLARE @Counter INT = 1;
DECLARE @NumCustomers INT = 500;
DECLARE @FirstNames TABLE (Name NVARCHAR(30));
DECLARE @LastNames TABLE (Name NVARCHAR(30));
DECLARE @States TABLE (StateCode NVARCHAR(2));

INSERT INTO @FirstNames VALUES 
('John'), ('Maria'), ('Robert'), ('Jennifer'), ('Michael'), ('Jessica'),
('William'), ('Patricia'), ('Richard'), ('Linda'), ('Joseph'), ('Barbara'),
('Thomas'), ('Elizabeth'), ('Charles'), ('Susan'), ('Christopher'), ('Karen'),
('Daniel'), ('Nancy'), ('David'), ('Margaret'), ('Mark'), ('Sandra');

INSERT INTO @LastNames VALUES
('Smith'), ('Johnson'), ('Williams'), ('Brown'), ('Jones'), ('Garcia'),
('Miller'), ('Davis'), ('Rodriguez'), ('Martinez'), ('Hernandez'), ('Lopez'),
('Gonzalez'), ('Wilson'), ('Anderson'), ('Thomas'), ('Taylor'), ('Moore'),
('Jackson'), ('Martin'), ('Lee'), ('Perez'), ('Thompson'), ('White');

INSERT INTO @States VALUES ('NY'), ('CA'), ('TX'), ('FL'), ('WA'), ('IL'), ('PA'), 
                           ('MA'), ('AZ'), ('CO'), ('GA'), ('NC'), ('MN'), ('TN'), 
                           ('OH'), ('MI'), ('IN'), ('VA'), ('WI'), ('MO');

WHILE @Counter <= @NumCustomers
BEGIN
    DECLARE @FirstName NVARCHAR(30) = (SELECT TOP 1 Name FROM @FirstNames ORDER BY NEWID());
    DECLARE @LastName NVARCHAR(30) = (SELECT TOP 1 Name FROM @LastNames ORDER BY NEWID());
    DECLARE @State NVARCHAR(2) = (SELECT TOP 1 StateCode FROM @States ORDER BY NEWID());
    DECLARE @JoinDate DATETIME = DATEADD(DAY, -ABS(CHECKSUM(NEWID()) % 730), '2018-01-01');
    
    INSERT INTO dbo.Customers 
    (CustomerCode, FirstName, LastName, Email, Phone, City, State, JoinDate, LoyaltyMember, MembershipTier)
    VALUES
    ('CUST' + FORMAT(@Counter, '000000'), 
     @FirstName, 
     @LastName,
     LOWER(@FirstName + '.' + @LastName + '@email.com'),
     '555-' + FORMAT(CAST(RAND()*9000 + 1000 AS INT), '0000'),
     'City ' + @State,
     @State,
     @JoinDate,
     CASE WHEN RAND() > 0.7 THEN 1 ELSE 0 END,
     CASE WHEN RAND() > 0.5 THEN 'Gold' WHEN RAND() > 0.7 THEN 'Platinum' ELSE 'Silver' END
    );
    
    SET @Counter = @Counter + 1;
END;

GO

-- ============================================================================
-- LINK INVOICES TO CUSTOMERS (RANDOM ASSIGNMENT)
-- ============================================================================

UPDATE ih
SET ih.CustomerID = (SELECT TOP 1 c.CustomerID FROM dbo.Customers c ORDER BY NEWID())
FROM dbo.InvoiceHeaders ih
WHERE ih.CustomerID IS NULL;

GO

-- ============================================================================
-- UPDATE CUSTOMER LIFETIME SPEND
-- ============================================================================

UPDATE dbo.Customers
SET TotalLifetimeSpend = COALESCE((
    SELECT SUM(id.QuantitySold * id.UnitPrice)
    FROM dbo.InvoiceHeaders ih
    INNER JOIN dbo.InvoiceDetails id ON ih.InvoiceID = id.InvoiceID
    WHERE ih.CustomerID = Customers.CustomerID
), 0),
LastPurchaseDate = (
    SELECT MAX(ih.InvoiceDate)
    FROM dbo.InvoiceHeaders ih
    WHERE ih.CustomerID = Customers.CustomerID
);

GO

-- ============================================================================
-- CALCULATE RFM SCORES
-- ============================================================================

INSERT INTO dbo.CustomerRFM
SELECT 
    c.CustomerID,
    DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) AS Recency,
    COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) AS Frequency,
    COALESCE(c.TotalLifetimeSpend, 0) AS Monetary,
    
    CASE 
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) <= 7 THEN 5
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) <= 30 THEN 4
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) <= 90 THEN 3
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) <= 180 THEN 2
        ELSE 1
    END AS R_Score,
    
    CASE 
        WHEN COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) >= 20 THEN 5
        WHEN COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) >= 10 THEN 4
        WHEN COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) >= 5 THEN 3
        WHEN COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) >= 2 THEN 2
        ELSE 1
    END AS F_Score,
    
    CASE 
        WHEN COALESCE(c.TotalLifetimeSpend, 0) >= 1000 THEN 5
        WHEN COALESCE(c.TotalLifetimeSpend, 0) >= 500 THEN 4
        WHEN COALESCE(c.TotalLifetimeSpend, 0) >= 250 THEN 3
        WHEN COALESCE(c.TotalLifetimeSpend, 0) >= 100 THEN 2
        ELSE 1
    END AS M_Score,
    
    NULL, NULL, GETDATE()
FROM dbo.Customers c;

GO

-- ============================================================================
-- UPDATE RFM SEGMENT
-- ============================================================================

UPDATE dbo.CustomerRFM
SET 
    RFM_Score = CAST(R_Score AS NVARCHAR(1)) + CAST(F_Score AS NVARCHAR(1)) + CAST(M_Score AS NVARCHAR(1)),
    Segment = CASE 
        WHEN R_Score >= 4 AND F_Score >= 4 AND M_Score >= 4 THEN 'Champions'
        WHEN R_Score >= 4 AND F_Score >= 3 AND M_Score >= 3 THEN 'Loyal Customers'
        WHEN R_Score >= 3 AND F_Score >= 3 AND M_Score >= 2 THEN 'Potential Loyalists'
        WHEN R_Score >= 3 AND F_Score >= 2 THEN 'At Risk'
        WHEN R_Score <= 2 AND M_Score >= 3 THEN 'Cant Lose Them'
        WHEN R_Score <= 1 THEN 'Lost'
        ELSE 'Need Attention'
    END;

GO

-- ============================================================================
-- CALCULATE CHURN RISK
-- ============================================================================

INSERT INTO dbo.CustomerChurnRisk
SELECT 
    c.CustomerID,
    DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) AS DaysSinceLastPurchase,
    COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) AS PurchaseFrequency,
    COALESCE((SELECT AVG(TotalAmount) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) AS AverageTicket,
    'Stable' AS MonthlySpendTrend,
    COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID AND InvoiceDate >= DATEADD(DAY, -30, GETDATE())), 0) AS VisitFrequency,
    0 AS DepartmentDiversity,
    
    CASE 
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) > 180 THEN 90
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) > 90 THEN 75
        WHEN DATEDIFF(DAY, COALESCE(c.LastPurchaseDate, c.JoinDate), CAST(GETDATE() AS DATE)) > 30 THEN 50
        WHEN COALESCE((SELECT COUNT(*) FROM dbo.InvoiceHeaders WHERE CustomerID = c.CustomerID), 0) = 1 THEN 60
        ELSE 25
    END AS ChurnRiskScore,
    
    NULL, NULL, GETDATE()
FROM dbo.Customers c;

GO

-- ============================================================================
-- UPDATE CHURN CATEGORIES
-- ============================================================================

UPDATE dbo.CustomerChurnRisk
SET 
    ChurnRiskCategory = CASE 
        WHEN ChurnRiskScore >= 75 THEN 'High'
        WHEN ChurnRiskScore >= 50 THEN 'Medium'
        ELSE 'Low'
    END,
    RecommendedAction = CASE 
        WHEN ChurnRiskScore >= 75 THEN 'Send win-back campaign, special offer'
        WHEN ChurnRiskScore >= 50 THEN 'Send promotional content, loyalty bonus'
        ELSE 'Maintain engagement, cross-sell opportunities'
    END;

GO

PRINT 'Customers and RFM data loaded successfully!';
