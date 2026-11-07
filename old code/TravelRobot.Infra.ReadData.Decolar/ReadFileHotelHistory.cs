using Serilog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.ReadData
{
    public class ReadFileHotelHistory : IReadFileHotelHistory
    {
        public const string DirectoryName = @"D:\Projetos\Viagem\HotelHistory";

        public List<HotelHistory> ReadLatestData()
        {
            try
            {
                List<HotelHistory> List = new List<HotelHistory>();
                List<string> Files = new List<string>();
                var DateFileSearched = new DateTime();
                var DateFileClear = new DateTime();
                var BiggestDate = new DateTime(2010, 1, 2);

                DirectoryInfo d = new DirectoryInfo(DirectoryName);

                FileInfo[] FilesSearched = d.GetFiles("*.csv").OrderByDescending(fi => fi.CreationTime).ToArray();

                foreach (FileInfo fileSearched in FilesSearched)
                {
                    DateFileSearched = DateTime.ParseExact(fileSearched.Name.Substring(fileSearched.Name.Length - 12, 8), "yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture);
                    if (DateFileSearched >= BiggestDate)
                    {
                        BiggestDate = DateFileSearched;
                        Files.Add(fileSearched.Name);
                    }
                }

                foreach (string fileClear in Files)
                {
                    DateFileClear = DateTime.ParseExact(fileClear.Substring(fileClear.Length - 12, 8), "yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture);
                    if (DateFileClear != BiggestDate)
                        Files.Remove(fileClear);
                }

                foreach (string FileItem in Files)
                {

                    using (var reader = new StreamReader(DirectoryName + @"\" + FileItem))
                    {

                        while (!reader.EndOfStream)
                        {
                            var item = new HotelHistory();
                            var line = reader.ReadLine();
                            var values = line.Split(';');

                            item.CurrentExecutionDate = DateTime.ParseExact(values[0], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.CityName = values[1];
                            item.HotelName = values[2];
                            item.Rating = values[3];
                            item.LastPrice = values[4];
                            item.DateLastPrice = DateTime.ParseExact(values[5], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.PriceDifferencePercentage = values[6];
                            item.BiggestPrice = values[7];
                            item.DateBiggestPrice = DateTime.ParseExact(values[8], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.LowestPrice = values[9];
                            item.DateLowestPrice = DateTime.ParseExact(values[10], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.NumberSearches = int.Parse(values[11]);
                            item.SumPrice = values[12];
                            item.AveragePrice = values[13];

                            List.Add(item);
                        }
                    }
                }
                return List;
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to reading the Hotel History csv file: {ex.Message}. ", ex);
                throw;
            }
        }
    }
}
