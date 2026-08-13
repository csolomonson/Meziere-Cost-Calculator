using System;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using CrystalDecisions.CrystalReports.Engine;
using CrystalDecisions.Shared;

namespace CrystalReportRenderer
{
    internal sealed class RenderRequest
    {
        public string reportPath { get; set; }
        public string parameterName { get; set; }
        public int partCostId { get; set; }
        public string server { get; set; }
        public string database { get; set; }
        public string username { get; set; }
        public string password { get; set; }
    }

    internal static class Program
    {
        private static int Main()
        {
            Console.InputEncoding = new UTF8Encoding(false);
            try
            {
                RenderRequest request = ReadRequest();
                Validate(request);
                Render(request);
                return 0;
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(
                    "{0}: {1}", exception.GetType().Name, exception.Message
                );
                return 1;
            }
        }

        private static RenderRequest ReadRequest()
        {
            string json = Console.In.ReadToEnd();
            if (String.IsNullOrWhiteSpace(json))
            {
                throw new InvalidDataException("The render request was empty.");
            }
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            return serializer.Deserialize<RenderRequest>(json);
        }

        private static void Validate(RenderRequest request)
        {
            if (request == null)
            {
                throw new InvalidDataException("The render request was invalid.");
            }
            if (String.IsNullOrWhiteSpace(request.reportPath) ||
                !Path.IsPathRooted(request.reportPath) ||
                !File.Exists(request.reportPath))
            {
                throw new FileNotFoundException("The Crystal report file was not found.");
            }
            if (String.IsNullOrWhiteSpace(request.parameterName))
            {
                throw new InvalidDataException("The report parameter name is required.");
            }
            if (request.partCostId <= 0)
            {
                throw new InvalidDataException("PartCostID must be positive.");
            }
            if (String.IsNullOrWhiteSpace(request.server) ||
                String.IsNullOrWhiteSpace(request.database) ||
                String.IsNullOrWhiteSpace(request.username) ||
                String.IsNullOrWhiteSpace(request.password))
            {
                throw new InvalidDataException("Database login information is incomplete.");
            }
        }

        private static void Render(RenderRequest request)
        {
            using (ReportDocument report = new ReportDocument())
            {
                report.Load(request.reportPath, OpenReportMethod.OpenReportByTempCopy);
                ApplyDatabaseLogin(report, request);
                report.SetParameterValue(request.parameterName, request.partCostId);
                report.Refresh();

                using (Stream pdf = report.ExportToStream(
                    ExportFormatType.PortableDocFormat
                ))
                using (Stream output = Console.OpenStandardOutput())
                {
                    pdf.CopyTo(output);
                    output.Flush();
                }
                report.Close();
            }
        }

        private static void ApplyDatabaseLogin(
            ReportDocument report,
            RenderRequest request
        )
        {
            report.SetDatabaseLogon(
                request.username,
                request.password,
                request.server,
                request.database,
                false
            );
            ApplyTableLogin(report.Database.Tables, request);
            foreach (ReportDocument subreport in report.Subreports)
            {
                ApplyDatabaseLogin(subreport, request);
            }
        }

        private static void ApplyTableLogin(
            Tables tables,
            RenderRequest request
        )
        {
            ConnectionInfo connection = new ConnectionInfo
            {
                ServerName = request.server,
                DatabaseName = request.database,
                UserID = request.username,
                Password = request.password,
                IntegratedSecurity = false
            };

            foreach (Table table in tables)
            {
                TableLogOnInfo login = table.LogOnInfo;
                login.ConnectionInfo = connection;
                table.ApplyLogOnInfo(login);
            }
        }
    }
}
