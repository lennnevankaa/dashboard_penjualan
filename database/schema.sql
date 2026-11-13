IF OBJECT_ID('dbo.stg_sales','U') IS NULL
CREATE TABLE dbo.stg_sales (
    TransactionID NVARCHAR(500), Delivery_Date NVARCHAR(500), OrderNumber NVARCHAR(500),
    No_Sales_Order NVARCHAR(500), Market_Place NVARCHAR(500), Bundling_Code NVARCHAR(500),
    Item_Code NVARCHAR(500), Client_Code NVARCHAR(500), Item_Name NVARCHAR(500),
    Selling_Price NVARCHAR(500), Total_Qty NVARCHAR(500), Line_Amount NVARCHAR(500),
    Line_Amount_Return NVARCHAR(500), Total_Amount NVARCHAR(500), RRP NVARCHAR(500),
    TOTAL_RRP NVARCHAR(500), DISC_VALUE NVARCHAR(500), ASP NVARCHAR(500),
    TOTAL_SALES NVARCHAR(500), SUBSIDI_MP NVARCHAR(500), PENJUALAN NVARCHAR(500),
    SETTLEMENT_AMOUNT NVARCHAR(500), Disc NVARCHAR(500), Created_Date NVARCHAR(500),
    Brand NVARCHAR(500), Bundling_Name NVARCHAR(500), COGS NVARCHAR(500),
    Total_COGS NVARCHAR(500), DNI_CBP NVARCHAR(500), Total_DNI_CBP NVARCHAR(500),
    Total_Promo NVARCHAR(500), Klaim_MIC NVARCHAR(500), Total_Klaim_MIC NVARCHAR(500),
    Support_DNI NVARCHAR(500), Total_Support NVARCHAR(500), Fee_Mp NVARCHAR(500),
    Total_Fee_Mp NVARCHAR(500), FEE_DNI NVARCHAR(500), FEE_DNI_8 NVARCHAR(500),
    loaded_at DATETIME2 NOT NULL CONSTRAINT DF_stg_sales_loaded_at DEFAULT SYSDATETIME()
);
GO

IF OBJECT_ID('dbo.stg_sales_clean','U') IS NULL
CREATE TABLE dbo.stg_sales_clean (
    transaction_id NVARCHAR(100) NOT NULL,
    delivery_date DATE NOT NULL,
    marketplace_id NVARCHAR(200) NOT NULL,
    marketplace_name NVARCHAR(200) NOT NULL,
    company_name NVARCHAR(100) NOT NULL,
    bundling_id NVARCHAR(100) NOT NULL,
    bundling_name NVARCHAR(255) NOT NULL,
    sku_code NVARCHAR(100) NOT NULL,
    product_name NVARCHAR(255) NULL,
    category_name NVARCHAR(100) NULL,
    total_qty INT NOT NULL,
    selling_price DECIMAL(18,2) NOT NULL,
    disc DECIMAL(18,2) NOT NULL,
    sales DECIMAL(18,2) NOT NULL,
    cogs DECIMAL(18,2) NOT NULL
);
GO

IF OBJECT_ID('dbo.dim_date','U') IS NULL
CREATE TABLE dbo.dim_date (
    sk_date INT IDENTITY(1,1) CONSTRAINT PK_dim_date PRIMARY KEY,
    delivery_date DATE NOT NULL CONSTRAINT UQ_dim_date UNIQUE,
    [day] TINYINT NOT NULL,
    [month] TINYINT NOT NULL,
    [year] SMALLINT NOT NULL,
    [quarter] NVARCHAR(2) NOT NULL
);
GO

IF OBJECT_ID('dbo.dim_marketplace','U') IS NULL
CREATE TABLE dbo.dim_marketplace (
    sk_marketplace INT IDENTITY(1,1) CONSTRAINT PK_dim_marketplace PRIMARY KEY,
    marketplace_id NVARCHAR(200) NOT NULL CONSTRAINT UQ_dim_marketplace UNIQUE,
    marketplace_name NVARCHAR(200) NOT NULL,
    company_name NVARCHAR(100) NOT NULL
);
GO

IF OBJECT_ID('dbo.dim_product','U') IS NULL
CREATE TABLE dbo.dim_product (
    sk_product INT IDENTITY(1,1) CONSTRAINT PK_dim_product PRIMARY KEY,
    sku_code NVARCHAR(100) NOT NULL CONSTRAINT UQ_dim_product UNIQUE,
    product_name NVARCHAR(255) NULL,
    category_name NVARCHAR(100) NULL
);
GO

IF OBJECT_ID('dbo.dim_bundling','U') IS NULL
CREATE TABLE dbo.dim_bundling (
    sk_bundling INT IDENTITY(1,1) CONSTRAINT PK_dim_bundling PRIMARY KEY,
    bundling_id NVARCHAR(100) NOT NULL CONSTRAINT UQ_dim_bundling UNIQUE,
    bundling_name NVARCHAR(255) NOT NULL
);
GO

IF OBJECT_ID('dbo.fact_sales','U') IS NULL
CREATE TABLE dbo.fact_sales (
    sk_sales BIGINT IDENTITY(1,1) CONSTRAINT PK_fact_sales PRIMARY KEY,
    sk_date INT NOT NULL CONSTRAINT FK_fact_date REFERENCES dbo.dim_date(sk_date),
    sk_product INT NOT NULL CONSTRAINT FK_fact_product REFERENCES dbo.dim_product(sk_product),
    sk_marketplace INT NOT NULL CONSTRAINT FK_fact_marketplace REFERENCES dbo.dim_marketplace(sk_marketplace),
    sk_bundling INT NOT NULL CONSTRAINT FK_fact_bundling REFERENCES dbo.dim_bundling(sk_bundling),
    transaction_id NVARCHAR(100) NOT NULL,
    total_qty INT NOT NULL,
    selling_price DECIMAL(18,2) NOT NULL,
    disc DECIMAL(18,2) NOT NULL,
    sales DECIMAL(18,2) NOT NULL,
    cogs DECIMAL(18,2) NOT NULL,
    CONSTRAINT UQ_fact_sales_trx UNIQUE (transaction_id, sk_product)
);
GO

IF OBJECT_ID('dbo.product_cluster','U') IS NULL
CREATE TABLE dbo.product_cluster (
    sk_product INT NOT NULL CONSTRAINT PK_product_cluster PRIMARY KEY,
    sku_code NVARCHAR(100) NOT NULL,
    product_name NVARCHAR(255) NULL,
    total_qty INT NOT NULL,
    total_sales DECIMAL(18,2) NOT NULL,
    total_disc DECIMAL(18,2) NOT NULL,
    last_delivery_date DATE NULL,
    qty_norm FLOAT NOT NULL,
    sales_norm FLOAT NOT NULL,
    disc_norm FLOAT NOT NULL,
    cluster_id INT NOT NULL,
    cluster_label NVARCHAR(50) NOT NULL,
    k INT NOT NULL,
    run_at DATETIME2 NOT NULL CONSTRAINT DF_product_cluster_run DEFAULT SYSDATETIME()
);
GO

IF OBJECT_ID('dbo.cluster_evaluation','U') IS NULL
CREATE TABLE dbo.cluster_evaluation (
    k INT NOT NULL CONSTRAINT PK_cluster_evaluation PRIMARY KEY,
    sse FLOAT NOT NULL,
    dbi FLOAT NOT NULL,
    is_best BIT NOT NULL,
    run_at DATETIME2 NOT NULL CONSTRAINT DF_cluster_eval_run DEFAULT SYSDATETIME()
);
GO