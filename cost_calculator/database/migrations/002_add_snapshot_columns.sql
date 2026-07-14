/*
    Add snapshot columns used by the costing UI.

    These are additive and safe to run more than once. Manufactured child
    costs are referenced by ucmManufacturedPartCostID; material/labor/machine
    splits are read from the referenced PartCosts row rather than stored as
    duplicate bucket columns on MaterialCostLines.
*/

USE [M2_ME];
GO

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH('dbo.PartCosts', 'ucpRetailUnitPrice') IS NULL
        ALTER TABLE dbo.PartCosts ADD ucpRetailUnitPrice DECIMAL(19,4) NULL;

    IF COL_LENGTH('dbo.PartCosts', 'ucpRetailPriceLevelsJson') IS NULL
        ALTER TABLE dbo.PartCosts ADD ucpRetailPriceLevelsJson NVARCHAR(MAX) NULL;

    IF COL_LENGTH('dbo.OperationCostLines', 'ucoExternalUnitCost') IS NULL
        ALTER TABLE dbo.OperationCostLines ADD ucoExternalUnitCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalUnitCost DEFAULT 0;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmHasManufacturingDetail') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmHasManufacturingDetail BIT NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmManufacturingMaterialCount') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmManufacturingMaterialCount INT NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmManufacturingOperationCount') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmManufacturingOperationCount INT NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmManufacturedPartCostID') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmManufacturedPartCostID INT NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmBackflush') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmBackflush BIT NOT NULL CONSTRAINT DF_MaterialCostLines_Backflush DEFAULT 1;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmRetailUnitPrice') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmRetailUnitPrice DECIMAL(19,4) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmPurchaseUnitCost') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmPurchaseUnitCost DECIMAL(19,4) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmMaterialPriceMode') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmMaterialPriceMode NVARCHAR(20) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmLastPOPurchaseUnitCost') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmLastPOPurchaseUnitCost DECIMAL(19,4) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmLastPOConversionFactor') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmLastPOConversionFactor DECIMAL(19,8) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmLastPOPurchaseUnit') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmLastPOPurchaseUnit NVARCHAR(50) NULL;

    IF COL_LENGTH('dbo.MaterialCostLines', 'ucmLastPOInventoryUnit') IS NULL
        ALTER TABLE dbo.MaterialCostLines ADD ucmLastPOInventoryUnit NVARCHAR(50) NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_MaterialCostLines_ManufacturedPartCostID' AND object_id = OBJECT_ID(N'dbo.MaterialCostLines'))
        CREATE INDEX IX_MaterialCostLines_ManufacturedPartCostID ON dbo.MaterialCostLines (ucmManufacturedPartCostID);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO
