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

    IF OBJECT_ID(N'dbo.PartCosts', N'U') IS NULL
        THROW 51000, 'dbo.PartCosts does not exist.', 1;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PartCosts_Recent' AND object_id = OBJECT_ID(N'dbo.PartCosts'))
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

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_PartCosts_PartID_Recent' AND object_id = OBJECT_ID(N'dbo.PartCosts'))
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

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
