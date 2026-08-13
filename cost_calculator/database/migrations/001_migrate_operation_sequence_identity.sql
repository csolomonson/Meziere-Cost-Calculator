/*
    One-time migration for OperationCostLines.ucoPartOperationLineID.

    Older app databases created this column as IDENTITY. That prevents the app
    from saving real operation sequence IDs such as 10, 20, 30 for each part
    cost. SQL Server cannot remove IDENTITY with ALTER COLUMN, so this script
    renames the old table as a backup, creates the corrected table, and copies
    the existing rows into it.
*/

USE [M2_ME];
GO

SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.OperationCostLines', N'U') IS NOT NULL
    AND COLUMNPROPERTY(
        OBJECT_ID(N'dbo.OperationCostLines'),
        N'ucoPartOperationLineID',
        'IsIdentity'
    ) = 1
BEGIN
    IF OBJECT_ID(N'dbo.OperationCostLines_IdentityBackup', N'U') IS NOT NULL
        THROW 51000, 'dbo.OperationCostLines_IdentityBackup already exists. Review or rename it before running this migration again.', 1;

    EXEC sp_rename N'dbo.OperationCostLines', N'OperationCostLines_IdentityBackup';
END;

IF OBJECT_ID(N'dbo.OperationCostLines', N'U') IS NULL
    AND OBJECT_ID(N'dbo.OperationCostLines_IdentityBackup', N'U') IS NOT NULL
BEGIN
    /*
        The table rename does not rename constraints.
        Rename the backup table's old constraints so the new table can reuse
        names like PK_OperationCostLines and DF_OperationCostLines_*.
    */

    DECLARE @constraintName sysname;
    DECLARE @newConstraintName sysname;
    DECLARE @qualifiedConstraintName NVARCHAR(300);

    DECLARE constraint_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT name
        FROM sys.objects
        WHERE parent_object_id = OBJECT_ID(N'dbo.OperationCostLines_IdentityBackup')
            AND type IN ('C', 'D', 'F', 'PK', 'UQ');

    OPEN constraint_cursor;

    FETCH NEXT FROM constraint_cursor INTO @constraintName;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @newConstraintName = LEFT(@constraintName + N'_IdentityBackup', 128);
        SET @qualifiedConstraintName = N'dbo.' + QUOTENAME(@constraintName);

        IF @constraintName <> @newConstraintName
            AND OBJECT_ID(N'dbo.' + QUOTENAME(@newConstraintName)) IS NULL
        BEGIN
            EXEC sp_rename
                @objname = @qualifiedConstraintName,
                @newname = @newConstraintName,
                @objtype = N'OBJECT';
        END;

        FETCH NEXT FROM constraint_cursor INTO @constraintName;
    END;

    CLOSE constraint_cursor;
    DEALLOCATE constraint_cursor;

    CREATE TABLE dbo.OperationCostLines (
        ucoPartOperationLineID INT NOT NULL,
        ucoPartCostID INT NOT NULL,

        ucoCostQuantity DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_CostQuantity DEFAULT 1,

        ucoQuantityPerAssembly DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_QtyPerAssembly DEFAULT 1,

        ucoWorkCenterID NVARCHAR(50) NULL,
        ucoOperationID NVARCHAR(50) NULL,
        ucoOperationDescription NVARCHAR(255) NULL,

        ucoSetupTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_SetupTimeHours DEFAULT 0,

        ucoCycleTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_CycleTimeHours DEFAULT 0,

        ucoBatchSize DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_BatchSize DEFAULT 1,

        ucoBatchTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_BatchTimeHours DEFAULT 0,

        ucoAutomated BIT NOT NULL
            CONSTRAINT DF_OperationCostLines_Automated DEFAULT 0,

        ucoMachineRunningHourlyCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_MachineRunningHourlyCost DEFAULT 0,

        ucoMachineOccupiedHourlyCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_MachineOccupiedHourlyCost DEFAULT 0,

        ucoMachineCostMarkup DECIMAL(9,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_MachineCostMarkup DEFAULT 1,

        ucoSetupLaborRate DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_SetupLaborRate DEFAULT 0,

        ucoBatchResetTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_BatchResetTimeHours DEFAULT 0,

        ucoBatchIdleTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_BatchIdleTimeHours DEFAULT 0,

        ucoUseAfterHoursIdle BIT NOT NULL
            CONSTRAINT DF_OperationCostLines_UseAfterHoursIdle DEFAULT 0,

        ucoStartTime NVARCHAR(5) NOT NULL
            CONSTRAINT DF_OperationCostLines_StartTime DEFAULT '',

        ucoAfterHoursIdleRateMultiplier DECIMAL(9,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AfterHoursIdleRateMultiplier DEFAULT 1,

        ucoAfterHoursIdleTimeHours DECIMAL(19,6) NOT NULL
            CONSTRAINT DF_OperationCostLines_AfterHoursIdleTimeHours DEFAULT 0,

        ucoBatchResetLaborRate DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_BatchResetLaborRate DEFAULT 0,

        ucoLaborMarkup DECIMAL(9,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_LaborMarkup DEFAULT 1,

        ucoExternalJob BIT NOT NULL
            CONSTRAINT DF_OperationCostLines_ExternalJob DEFAULT 0,

        ucoLastPO NVARCHAR(50) NULL,
        ucoLastPOCost DECIMAL(19,4) NULL,
        ucoLastPODate DATE NULL,

        ucoExternalCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_ExternalCost DEFAULT 0,

        ucoExternalOperationMarkup DECIMAL(9,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_ExternalOperationMarkup DEFAULT 1,

        ucoAdditionalCostPerPart DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AdditionalCostPerPart DEFAULT 0,

        ucoAdditionalCostTotal DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AdditionalCostTotal DEFAULT 0,

        ucoAdditionalCostMarkup DECIMAL(9,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AdditionalCostMarkup DEFAULT 1,

        ucoAdditionalCostRawCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AdditionalRawCost DEFAULT 0,

        ucoAdditionalCostMarkedUpCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_AdditionalMarkedUpCost DEFAULT 0,

        ucoMachineRawCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_MachineRawCost DEFAULT 0,

        ucoMachineMarkedUpCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_MachineMarkedUpCost DEFAULT 0,

        ucoLaborRawCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_LaborRawCost DEFAULT 0,

        ucoLaborMarkedUpCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_LaborMarkedUpCost DEFAULT 0,

        ucoExternalOperationRawCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_ExternalOperationRawCost DEFAULT 0,

        ucoExternalOperationMarkedUpCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_ExternalOperationMarkedUpCost DEFAULT 0,

        ucoLineRawCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_LineRawCost DEFAULT 0,

        ucoLineMarkedUpCost DECIMAL(19,4) NOT NULL
            CONSTRAINT DF_OperationCostLines_LineMarkedUpCost DEFAULT 0,

        CONSTRAINT PK_OperationCostLines
            PRIMARY KEY (ucoPartCostID, ucoPartOperationLineID),

        CONSTRAINT FK_OperationCostLines_PartCosts
            FOREIGN KEY (ucoPartCostID)
            REFERENCES dbo.PartCosts(ucpPartCostID)
    );

    INSERT INTO dbo.OperationCostLines (
        ucoPartOperationLineID,
        ucoPartCostID,
        ucoCostQuantity,
        ucoQuantityPerAssembly,
        ucoWorkCenterID,
        ucoOperationID,
        ucoOperationDescription,
        ucoSetupTimeHours,
        ucoCycleTimeHours,
        ucoBatchSize,
        ucoBatchTimeHours,
        ucoAutomated,
        ucoMachineRunningHourlyCost,
        ucoMachineOccupiedHourlyCost,
        ucoMachineCostMarkup,
        ucoSetupLaborRate,
        ucoBatchResetTimeHours,
        ucoBatchIdleTimeHours,
        ucoUseAfterHoursIdle,
        ucoStartTime,
        ucoAfterHoursIdleRateMultiplier,
        ucoAfterHoursIdleTimeHours,
        ucoBatchResetLaborRate,
        ucoLaborMarkup,
        ucoExternalJob,
        ucoLastPO,
        ucoLastPOCost,
        ucoLastPODate,
        ucoExternalCost,
        ucoExternalOperationMarkup,
        ucoAdditionalCostPerPart,
        ucoAdditionalCostTotal,
        ucoAdditionalCostMarkup,
        ucoAdditionalCostRawCost,
        ucoAdditionalCostMarkedUpCost,
        ucoMachineRawCost,
        ucoMachineMarkedUpCost,
        ucoLaborRawCost,
        ucoLaborMarkedUpCost,
        ucoExternalOperationRawCost,
        ucoExternalOperationMarkedUpCost,
        ucoLineRawCost,
        ucoLineMarkedUpCost
    )
    SELECT
        ucoPartOperationLineID,
        ucoPartCostID,
        ucoCostQuantity,
        ucoQuantityPerAssembly,
        ucoWorkCenterID,
        ucoOperationID,
        ucoOperationDescription,
        ucoSetupTimeHours,
        ucoCycleTimeHours,
        ucoBatchSize,
        ucoBatchTimeHours,
        ucoAutomated,
        ucoMachineRunningHourlyCost,
        ucoMachineOccupiedHourlyCost,
        ucoMachineCostMarkup,
        ucoSetupLaborRate,
        ucoBatchResetTimeHours,
        ucoBatchIdleTimeHours,
        ucoUseAfterHoursIdle,
        ucoStartTime,
        ucoAfterHoursIdleRateMultiplier,
        ucoAfterHoursIdleTimeHours,
        ucoBatchResetLaborRate,
        ucoLaborMarkup,
        ucoExternalJob,
        ucoLastPO,
        ucoLastPOCost,
        ucoLastPODate,
        ucoExternalCost,
        ucoExternalOperationMarkup,
        ucoAdditionalCostPerPart,
        ucoAdditionalCostTotal,
        ucoAdditionalCostMarkup,
        ucoAdditionalCostRawCost,
        ucoAdditionalCostMarkedUpCost,
        ucoMachineRawCost,
        ucoMachineMarkedUpCost,
        ucoLaborRawCost,
        ucoLaborMarkedUpCost,
        ucoExternalOperationRawCost,
        ucoExternalOperationMarkedUpCost,
        ucoLineRawCost,
        ucoLineMarkedUpCost
    FROM dbo.OperationCostLines_IdentityBackup;

    CREATE INDEX IX_OperationCostLines_PartCostID
        ON dbo.OperationCostLines (ucoPartCostID);
END;

COMMIT TRANSACTION;
GO

SELECT
    COLUMNPROPERTY(
        OBJECT_ID(N'dbo.OperationCostLines'),
        N'ucoPartOperationLineID',
        'IsIdentity'
    ) AS ucoPartOperationLineIDIsIdentity;
GO
