/*
    create_costing_tables.sql

    Creates costing project tables:
      - PartCosts
      - OperationCostLines
      - MaterialCostLines
      - DefaultCosts

    Also inserts the __GLOBAL__ DefaultCosts row and creates useful indexes.
*/

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.PartCosts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.PartCosts (
            ucpPartCostID INT IDENTITY(1,1) NOT NULL,

            ucpPartID NVARCHAR(50) NOT NULL,
            ucpPartRevision NVARCHAR(50) NOT NULL CONSTRAINT DF_PartCosts_PartRevision DEFAULT '',
            ucpPartDescription NVARCHAR(255) NULL,

            ucpDateCosted DATETIME2 NOT NULL CONSTRAINT DF_PartCosts_DateCosted DEFAULT SYSUTCDATETIME(),
            ucpCostedBy NVARCHAR(100) NULL,

            ucpMaterialsRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MaterialsRawCost DEFAULT 0,
            ucpMaterialsMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MaterialsMarkedUpCost DEFAULT 0,

            ucpMachineTimeRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MachineTimeRawCost DEFAULT 0,
            ucpMachineTimeMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_MachineTimeMarkedUpCost DEFAULT 0,

            ucpLaborRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_LaborRawCost DEFAULT 0,
            ucpLaborMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_LaborMarkedUpCost DEFAULT 0,

            ucpExternalOperationsRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_ExternalOperationsRawCost DEFAULT 0,
            ucpExternalOperationsMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_ExternalOperationsMarkedUpCost DEFAULT 0,

            ucpTotalRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_TotalRawCost DEFAULT 0,
            ucpTotalMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_PartCosts_TotalMarkedUpCost DEFAULT 0,

            ucpNotes NVARCHAR(MAX) NULL,

            CONSTRAINT PK_PartCosts PRIMARY KEY (ucpPartCostID)
        );
    END;

    IF OBJECT_ID(N'dbo.OperationCostLines', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.OperationCostLines (
            ucoPartOperationLineID INT IDENTITY(1,1) NOT NULL,
            ucoPartCostID INT NOT NULL,

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
            ucoMachineCostMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineCostMarkup DEFAULT 0,

            ucoSetupLaborRate DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_SetupLaborRate DEFAULT 0,
            ucoBatchResetTimeHours DECIMAL(19,6) NOT NULL CONSTRAINT DF_OperationCostLines_BatchResetTimeHours DEFAULT 0,
            ucoBatchResetLaborRate DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_BatchResetLaborRate DEFAULT 0,
            ucoLaborMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborMarkup DEFAULT 0,

            ucoExternalJob BIT NOT NULL CONSTRAINT DF_OperationCostLines_ExternalJob DEFAULT 0,
            ucoLastPO NVARCHAR(50) NULL,
            ucoLastPOCost DECIMAL(19,4) NULL,
            ucoExternalOperationMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationMarkup DEFAULT 0,

            ucoMachineRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineRawCost DEFAULT 0,
            ucoMachineMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_MachineMarkedUpCost DEFAULT 0,

            ucoLaborRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborRawCost DEFAULT 0,
            ucoLaborMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LaborMarkedUpCost DEFAULT 0,

            ucoExternalOperationRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationRawCost DEFAULT 0,
            ucoExternalOperationMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_ExternalOperationMarkedUpCost DEFAULT 0,

            ucoLineRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LineRawCost DEFAULT 0,
            ucoLineMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_OperationCostLines_LineMarkedUpCost DEFAULT 0,

            CONSTRAINT PK_OperationCostLines PRIMARY KEY (ucoPartOperationLineID),

            CONSTRAINT FK_OperationCostLines_PartCosts
                FOREIGN KEY (ucoPartCostID)
                REFERENCES dbo.PartCosts(ucpPartCostID)
        );
    END;

    IF OBJECT_ID(N'dbo.MaterialCostLines', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.MaterialCostLines (
            ucmPartMaterialLineID INT IDENTITY(1,1) NOT NULL,
            ucmPartCostID INT NOT NULL,

            ucmMaterialID NVARCHAR(50) NULL,
            ucmMaterialDescription NVARCHAR(255) NULL,

            ucmQtyPerAssembly DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_QtyPerAssembly DEFAULT 0,
            ucmIsPurchased BIT NOT NULL CONSTRAINT DF_MaterialCostLines_IsPurchased DEFAULT 0,

            ucmLastPO NVARCHAR(50) NULL,
            ucmLastPOCost DECIMAL(19,4) NULL,

            ucmUnitCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_UnitCost DEFAULT 0,
            ucmMinimumPurchaseQty DECIMAL(19,6) NOT NULL CONSTRAINT DF_MaterialCostLines_MinimumPurchaseQty DEFAULT 0,

            ucmMaterialMarkup DECIMAL(9,4) NOT NULL CONSTRAINT DF_MaterialCostLines_MaterialMarkup DEFAULT 0,

            ucmRawCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_RawCost DEFAULT 0,
            ucmMarkedUpCost DECIMAL(19,4) NOT NULL CONSTRAINT DF_MaterialCostLines_MarkedUpCost DEFAULT 0,

            CONSTRAINT PK_MaterialCostLines PRIMARY KEY (ucmPartMaterialLineID),

            CONSTRAINT FK_MaterialCostLines_PartCosts
                FOREIGN KEY (ucmPartCostID)
                REFERENCES dbo.PartCosts(ucpPartCostID)
        );
    END;

    IF OBJECT_ID(N'dbo.DefaultCosts', N'U') IS NULL
    BEGIN
        CREATE TABLE DefaultCosts (
        ucdDefaultCostID INT IDENTITY(1,1) NOT NULL,

        ucdWorkCenterID NVARCHAR(50) NOT NULL,
        ucdMinimumQuantity DECIMAL(19,6) NOT NULL,

        ucdDefaultLaborHourlyCost DECIMAL(19,4) NULL,
        ucdDefaultMachineRunningHourlyCost DECIMAL(19,4) NULL,
        ucdDefaultMachineOccupiedHourlyCost DECIMAL(19,4) NULL,

        ucdDefaultMaterialMarkup DECIMAL(9,4) NULL,
        ucdDefaultLaborMarkup DECIMAL(9,4) NULL,
        ucdDefaultMachineCostMarkup DECIMAL(9,4) NULL,
        ucdDefaultExternalOperationMarkup DECIMAL(9,4) NULL,

        CONSTRAINT PK_DefaultCosts
            PRIMARY KEY (ucdDefaultCostID),

        CONSTRAINT UQ_DefaultCosts_WorkCenter_MinQty
            UNIQUE (ucdWorkCenterID, ucdMinimumQuantity),

        CONSTRAINT CK_DefaultCosts_MinQty_Positive
            CHECK (ucdMinimumQuantity > 0)
    );
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM dbo.DefaultCosts
        WHERE ucdWorkCenterID = N'__GLOBAL__'
    )
    BEGIN
        INSERT INTO dbo.DefaultCosts (
            ucdWorkCenterID,
            ucdDefaultLaborHourlyCost,
            ucdDefaultMachineRunningHourlyCost,
            ucdDefaultMachineOccupiedHourlyCost,
            ucdDefaultMaterialMarkup,
            ucdDefaultLaborMarkup,
            ucdDefaultMachineCostMarkup,
            ucdDefaultExternalOperationMarkup
        )
        VALUES (
            N'__GLOBAL__',
            0,
            0,
            0,
            0,
            0,
            0,
            0
        );
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = N'IX_PartCosts_PartID_Revision'
          AND object_id = OBJECT_ID(N'dbo.PartCosts')
    )
    BEGIN
        CREATE INDEX IX_PartCosts_PartID_Revision
        ON dbo.PartCosts (ucpPartID, ucpPartRevision);
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = N'IX_OperationCostLines_PartCostID'
          AND object_id = OBJECT_ID(N'dbo.OperationCostLines')
    )
    BEGIN
        CREATE INDEX IX_OperationCostLines_PartCostID
        ON dbo.OperationCostLines (ucoPartCostID);
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = N'IX_MaterialCostLines_PartCostID'
          AND object_id = OBJECT_ID(N'dbo.MaterialCostLines')
    )
    BEGIN
        CREATE INDEX IX_MaterialCostLines_PartCostID
        ON dbo.MaterialCostLines (ucmPartCostID);
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
