/*
    reset_schema.sql

    DESTRUCTIVE: drops and recreates all costing project tables.

    Creates costing project tables:
      - PartCosts
      - OperationCostLines
      - MaterialCostLines
      - CostingGlobalDefaults
      - MachineCostDefaults
      - MarkupBreaks
      - CostingSettings
*/

USE [M2_ME];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.MaterialCostLines', N'U') IS NOT NULL
        DROP TABLE dbo.MaterialCostLines;

    IF OBJECT_ID(N'dbo.OperationCostLines', N'U') IS NOT NULL
        DROP TABLE dbo.OperationCostLines;

    IF OBJECT_ID(N'dbo.PartCosts', N'U') IS NOT NULL
        DROP TABLE dbo.PartCosts;

    IF OBJECT_ID(N'dbo.MarkupBreaks', N'U') IS NOT NULL
        DROP TABLE dbo.MarkupBreaks;

    IF OBJECT_ID(N'dbo.MachineCostDefaults', N'U') IS NOT NULL
        DROP TABLE dbo.MachineCostDefaults;

    IF OBJECT_ID(N'dbo.CostingGlobalDefaults', N'U') IS NOT NULL
        DROP TABLE dbo.CostingGlobalDefaults;

    IF OBJECT_ID(N'dbo.CostingSettings', N'U') IS NOT NULL
        DROP TABLE dbo.CostingSettings;

    IF OBJECT_ID(N'dbo.DefaultCosts', N'U') IS NOT NULL
        DROP TABLE dbo.DefaultCosts;

    CREATE TABLE dbo.PartCosts (
            ucpPartCostID INT IDENTITY(1,1) NOT NULL,
            ucpPartID NVARCHAR(50) NOT NULL,
            ucpPartRevision NVARCHAR(50) NOT NULL CONSTRAINT DF_PartCosts_PartRevision DEFAULT '',
            ucpPartDescription NVARCHAR(255) NULL,
            ucpCostQuantity DECIMAL(19,6) NOT NULL CONSTRAINT DF_PartCosts_CostQuantity DEFAULT 1,
            ucpDateCosted DATETIME2 NOT NULL CONSTRAINT DF_PartCosts_DateCosted DEFAULT SYSUTCDATETIME(),
            ucpCostedBy NVARCHAR(100) NULL,
            ucpRetailUnitPrice DECIMAL(19,4) NULL,
            ucpRetailPriceLevelsJson NVARCHAR(MAX) NULL,
            ucpMaterialsRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MaterialsRawCost DEFAULT 0,
            ucpMaterialsMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MaterialsMarkedUpCost DEFAULT 0,
            ucpMachineTimeRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MachineTimeRawCost DEFAULT 0,
            ucpMachineTimeMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MachineTimeMarkedUpCost DEFAULT 0,
            ucpLaborRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_LaborRawCost DEFAULT 0,
            ucpLaborMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_LaborMarkedUpCost DEFAULT 0,
            ucpExternalOperationsRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_ExternalOperationsRawCost DEFAULT 0,
            ucpExternalOperationsMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_ExternalOperationsMarkedUpCost DEFAULT 0,
            ucpAdditionalRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_AdditionalRawCost DEFAULT 0,
            ucpAdditionalMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_AdditionalMarkedUpCost DEFAULT 0,
            ucpTotalRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_TotalRawCost DEFAULT 0,
            ucpTotalMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_TotalMarkedUpCost DEFAULT 0,
            ucpUnitRawCost DECIMAL(19,6) NOT NULL CONSTRAINT DF_PartCosts_UnitRawCost DEFAULT 0,
            ucpUnitMarkedUpCost DECIMAL(19,6) NOT NULL CONSTRAINT DF_PartCosts_UnitMarkedUpCost DEFAULT 0,
            ucpIsCurrent BIT NOT NULL CONSTRAINT DF_PartCosts_IsCurrent DEFAULT 0,
            ucpNotes NVARCHAR(MAX) NULL,
            CONSTRAINT PK_PartCosts PRIMARY KEY (ucpPartCostID)
    );

    CREATE TABLE dbo.OperationCostLines (
            ucoPartOperationLineID INT NOT NULL,
            ucoPartCostID INT NOT NULL,
            ucoCostQuantity DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_CostQuantity DEFAULT 1,
            ucoQuantityPerAssembly DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_QtyPerAssembly DEFAULT 1,
            ucoWorkCenterID NVARCHAR(50) NULL,
            ucoOperationID NVARCHAR(50) NULL,
            ucoOperationDescription NVARCHAR(255) NULL,
            ucoSetupTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_SetupTimeHours DEFAULT 0,
            ucoCycleTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_CycleTimeHours DEFAULT 0,
            ucoBatchSize DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_BatchSize DEFAULT 1,
            ucoBatchTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_BatchTimeHours DEFAULT 0,
            ucoAutomated BIT NOT NULL CONSTRAINT DF_OperationCostLines_Automated DEFAULT 0,
            ucoMachineRunningHourlyCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineRunningHourlyCost DEFAULT 0,
            ucoMachineOccupiedHourlyCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineOccupiedHourlyCost DEFAULT 0,
            ucoMachineCostMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineCostMarkup DEFAULT 1,
            ucoSetupLaborRate DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_SetupLaborRate DEFAULT 0,
            ucoBatchResetTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_BatchResetTimeHours DEFAULT 0,
            ucoBatchIdleTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_BatchIdleTimeHours DEFAULT 0,
            ucoUseAfterHoursIdle BIT NOT NULL CONSTRAINT DF_OperationCostLines_UseAfterHoursIdle DEFAULT 0,
            ucoStartTime NVARCHAR(5) NOT NULL CONSTRAINT DF_OperationCostLines_StartTime DEFAULT '',
            ucoAfterHoursIdleRateMultiplier DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_AfterHoursIdleRateMultiplier DEFAULT 1,
            ucoAfterHoursIdleTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_AfterHoursIdleTimeHours DEFAULT 0,
            ucoBatchResetLaborRate DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_BatchResetLaborRate DEFAULT 0,
            ucoLaborMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborMarkup DEFAULT 1,
            ucoExternalJob BIT NOT NULL CONSTRAINT DF_OperationCostLines_ExternalJob DEFAULT 0,
            ucoLastPO NVARCHAR(50) NULL,
            ucoLastPOCost DECIMAL(19,4) NULL,
            ucoLastPODate DATE NULL,
            ucoExternalUnitCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalUnitCost DEFAULT 0,
            ucoExternalCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalCost DEFAULT 0,
            ucoExternalOperationMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationMarkup DEFAULT 1,
            ucoAdditionalCostPerPart DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_AdditionalCostPerPart DEFAULT 0,
            ucoAdditionalCostTotal DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_AdditionalCostTotal DEFAULT 0,
            ucoAdditionalCostMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_AdditionalCostMarkup DEFAULT 1,
            ucoAdditionalCostRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_AdditionalRawCost DEFAULT 0,
            ucoAdditionalCostMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_AdditionalMarkedUpCost DEFAULT 0,
            ucoMachineRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineRawCost DEFAULT 0,
            ucoMachineMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineMarkedUpCost DEFAULT 0,
            ucoLaborRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborRawCost DEFAULT 0,
            ucoLaborMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborMarkedUpCost DEFAULT 0,
            ucoExternalOperationRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationRawCost DEFAULT 0,
            ucoExternalOperationMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationMarkedUpCost DEFAULT 0,
            ucoLineRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LineRawCost DEFAULT 0,
            ucoLineMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LineMarkedUpCost DEFAULT 0,
            CONSTRAINT PK_OperationCostLines PRIMARY KEY (ucoPartCostID, ucoPartOperationLineID),
            CONSTRAINT FK_OperationCostLines_PartCosts FOREIGN KEY (ucoPartCostID) REFERENCES dbo.PartCosts(ucpPartCostID)
    );

    CREATE TABLE dbo.MaterialCostLines (
            ucmPartMaterialLineID INT IDENTITY(1,1) NOT NULL,
            ucmPartCostID INT NOT NULL,
            ucmCostQuantity DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_CostQuantity DEFAULT 1,
            ucmMaterialID NVARCHAR(50) NULL,
            ucmMaterialDescription NVARCHAR(255) NULL,
            ucmQtyPerAssembly DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_QtyPerAssembly DEFAULT 0,
            ucmTotalQuantityRequired DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_TotalQty DEFAULT 0,
            ucmBackflush BIT NOT NULL CONSTRAINT DF_MaterialCostLines_Backflush DEFAULT 1,
            ucmIsPurchased BIT NOT NULL CONSTRAINT DF_MaterialCostLines_IsPurchased DEFAULT 0,
            ucmCostSource NVARCHAR(50) NULL,
            ucmHasManufacturingDetail BIT NULL,
            ucmManufacturingMaterialCount INT NULL,
            ucmManufacturingOperationCount INT NULL,
            ucmManufacturedPartCostID INT NULL,
            ucmLastPO NVARCHAR(50) NULL,
            ucmLastPOCost DECIMAL(19,4) NULL,
            ucmLastPODate DATE NULL,
            ucmRetailUnitPrice DECIMAL(19,4) NULL,
            ucmUnitCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_UnitCost DEFAULT 0,
            ucmPurchaseUnitCost DECIMAL(19,4) NULL,
            ucmMaterialPriceMode NVARCHAR(20) NULL,
            ucmLastPOPurchaseUnitCost DECIMAL(19,4) NULL,
            ucmLastPOConversionFactor DECIMAL(19,8) NULL,
            ucmLastPOPurchaseUnit NVARCHAR(50) NULL,
            ucmLastPOInventoryUnit NVARCHAR(50) NULL,
            ucmMinimumPurchaseQty DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_MinimumPurchaseQty DEFAULT 0,
            ucmMaterialMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MaterialCostLines_MaterialMarkup DEFAULT 1,
            ucmWasteQuantity DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_WasteQuantity DEFAULT 0,
            ucmRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_RawCost DEFAULT 0,
            ucmMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_MarkedUpCost DEFAULT 0,
            CONSTRAINT PK_MaterialCostLines PRIMARY KEY (ucmPartMaterialLineID),
            CONSTRAINT FK_MaterialCostLines_PartCosts FOREIGN KEY (ucmPartCostID) REFERENCES dbo.PartCosts(ucpPartCostID)
    );

    CREATE TABLE dbo.CostingGlobalDefaults (
            ucgGlobalDefaultID INT IDENTITY(1,1) NOT NULL,
            ucgDefaultLaborHourlyCost DECIMAL(19,4) NULL,
            ucgDefaultMachineRunningHourlyCost DECIMAL(19,4) NULL,
            ucgDefaultMachineOccupiedHourlyCost DECIMAL(19,4) NULL,
            ucgDefaultBatchResetTimeHours DECIMAL(19,6) NULL,
            ucgDefaultBatchIdleTimeHours DECIMAL(19,6) NULL,
            ucgDefaultFirstShiftStart NVARCHAR(5) NOT NULL CONSTRAINT DF_CostingGlobalDefaults_FirstShiftStart DEFAULT N'06:00',
            ucgDefaultFirstShiftEnd NVARCHAR(5) NOT NULL CONSTRAINT DF_CostingGlobalDefaults_FirstShiftEnd DEFAULT N'14:30',
            ucgDefaultAfterHoursIdleRateMultiplier DECIMAL(9,4) NOT NULL CONSTRAINT DF_CostingGlobalDefaults_AfterHoursIdleRateMultiplier DEFAULT 1,
            ucgUpdatedDate DATETIME2 NOT NULL CONSTRAINT DF_CostingGlobalDefaults_UpdatedDate DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_CostingGlobalDefaults PRIMARY KEY (ucgGlobalDefaultID)
    );

    CREATE TABLE dbo.MachineCostDefaults (
            ucmMachineDefaultID INT IDENTITY(1,1) NOT NULL,
            ucmWorkCenterID NVARCHAR(50) NOT NULL,
            ucmDefaultLaborHourlyCost DECIMAL(19,4) NULL,
            ucmDefaultMachineRunningHourlyCost DECIMAL(19,4) NULL,
            ucmDefaultMachineOccupiedHourlyCost DECIMAL(19,4) NULL,
            ucmDefaultBatchResetTimeHours DECIMAL(19,6) NULL,
            ucmDefaultBatchIdleTimeHours DECIMAL(19,6) NULL,
            ucmUpdatedDate DATETIME2 NOT NULL CONSTRAINT DF_MachineCostDefaults_UpdatedDate DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_MachineCostDefaults PRIMARY KEY (ucmMachineDefaultID),
            CONSTRAINT UQ_MachineCostDefaults_WorkCenter UNIQUE (ucmWorkCenterID)
    );

    CREATE TABLE dbo.MarkupBreaks (
            umbMarkupBreakID INT IDENTITY(1,1) NOT NULL,
            umbPartID NVARCHAR(50) NULL,
            umbPartRevision NVARCHAR(50) NULL,
            umbMinimumQuantity DECIMAL(19,6) NOT NULL,
            umbMaterialMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MarkupBreaks_MaterialMarkup DEFAULT 1,
            umbLaborMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MarkupBreaks_LaborMarkup DEFAULT 1,
            umbMachineCostMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MarkupBreaks_MachineCostMarkup DEFAULT 1,
            umbExternalOperationMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MarkupBreaks_ExternalOperationMarkup DEFAULT 1,
            umbAdditionalCostMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MarkupBreaks_AdditionalCostMarkup DEFAULT 1,
            umbUpdatedDate DATETIME2 NOT NULL CONSTRAINT DF_MarkupBreaks_UpdatedDate DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_MarkupBreaks PRIMARY KEY (umbMarkupBreakID),
            CONSTRAINT CK_MarkupBreaks_MinQty_Positive CHECK (umbMinimumQuantity > 0),
            CONSTRAINT CK_MarkupBreaks_PartScope CHECK (
                (umbPartID IS NULL AND umbPartRevision IS NULL)
                OR (umbPartID IS NOT NULL AND umbPartRevision IS NOT NULL)
            )
    );

    CREATE UNIQUE INDEX UQ_MarkupBreaks_Global_MinQty
        ON dbo.MarkupBreaks (umbMinimumQuantity)
        WHERE umbPartID IS NULL;

    CREATE UNIQUE INDEX UQ_MarkupBreaks_Part_MinQty
        ON dbo.MarkupBreaks (umbPartID, umbPartRevision, umbMinimumQuantity)
        WHERE umbPartID IS NOT NULL;

    CREATE TABLE dbo.CostingSettings (
            ucsSettingKey NVARCHAR(100) NOT NULL,
            ucsSettingValue NVARCHAR(MAX) NULL,
            ucsUpdatedDate DATETIME2 NOT NULL CONSTRAINT DF_CostingSettings_UpdatedDate DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_CostingSettings PRIMARY KEY (ucsSettingKey)
    );

    INSERT INTO dbo.CostingSettings (ucsSettingKey, ucsSettingValue)
    VALUES (N'firstShiftStart', N'06:00');

    INSERT INTO dbo.CostingSettings (ucsSettingKey, ucsSettingValue)
    VALUES (N'firstShiftEnd', N'14:30');

    INSERT INTO dbo.CostingSettings (ucsSettingKey, ucsSettingValue)
    VALUES (N'afterHoursIdleMultiplier', N'1');

    INSERT INTO dbo.CostingGlobalDefaults (
        ucgDefaultLaborHourlyCost,
        ucgDefaultMachineRunningHourlyCost,
        ucgDefaultMachineOccupiedHourlyCost,
        ucgDefaultBatchResetTimeHours,
        ucgDefaultBatchIdleTimeHours
    )
    VALUES (0, 0, 0, 0, 0);

    INSERT INTO dbo.MarkupBreaks (
        umbPartID,
        umbPartRevision,
        umbMinimumQuantity,
        umbMaterialMarkup,
        umbLaborMarkup,
        umbMachineCostMarkup,
        umbExternalOperationMarkup,
        umbAdditionalCostMarkup
    )
    VALUES (NULL, NULL, 1, 1, 1, 1, 1, 1);

    CREATE INDEX IX_PartCosts_PartID_Revision
        ON dbo.PartCosts (ucpPartID, ucpPartRevision);

    CREATE INDEX IX_PartCosts_Recent
        ON dbo.PartCosts (ucpDateCosted DESC, ucpPartCostID DESC)
        INCLUDE (
            ucpPartID, ucpPartRevision, ucpPartDescription, ucpCostQuantity, ucpCostedBy,
            ucpUnitRawCost, ucpUnitMarkedUpCost,
            ucpMaterialsRawCost, ucpMaterialsMarkedUpCost,
            ucpMachineTimeRawCost, ucpMachineTimeMarkedUpCost,
            ucpLaborRawCost, ucpLaborMarkedUpCost,
            ucpExternalOperationsRawCost, ucpExternalOperationsMarkedUpCost,
            ucpAdditionalRawCost, ucpAdditionalMarkedUpCost,
            ucpTotalRawCost, ucpTotalMarkedUpCost, ucpIsCurrent
        );

    CREATE INDEX IX_PartCosts_PartID_Recent
        ON dbo.PartCosts (ucpPartID, ucpDateCosted DESC, ucpPartCostID DESC)
        INCLUDE (
            ucpPartRevision, ucpPartDescription, ucpCostQuantity, ucpCostedBy,
            ucpUnitRawCost, ucpUnitMarkedUpCost,
            ucpMaterialsRawCost, ucpMaterialsMarkedUpCost,
            ucpMachineTimeRawCost, ucpMachineTimeMarkedUpCost,
            ucpLaborRawCost, ucpLaborMarkedUpCost,
            ucpExternalOperationsRawCost, ucpExternalOperationsMarkedUpCost,
            ucpAdditionalRawCost, ucpAdditionalMarkedUpCost,
            ucpTotalRawCost, ucpTotalMarkedUpCost, ucpIsCurrent
        );

    CREATE UNIQUE INDEX UQ_PartCosts_Current
        ON dbo.PartCosts (ucpPartID, ucpPartRevision)
        WHERE ucpIsCurrent = 1;

    CREATE INDEX IX_OperationCostLines_PartCostID
        ON dbo.OperationCostLines (ucoPartCostID);

    CREATE INDEX IX_MaterialCostLines_PartCostID
        ON dbo.MaterialCostLines (ucmPartCostID);

    CREATE INDEX IX_MaterialCostLines_ManufacturedPartCostID
        ON dbo.MaterialCostLines (ucmManufacturedPartCostID);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
