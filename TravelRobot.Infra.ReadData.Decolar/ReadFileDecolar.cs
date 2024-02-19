using Serilog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.ReadData.Decolar
{
    public class ReadFileDecolar : IReadFileDecolar
    {

        public const string DirectoryName = @"D:\Projetos\Viagem\Hoteis_Por_Dia\";

        public List<Hotel> ReadLatestData()
        {
            try
            {
                List<Hotel> List = new List<Hotel>();
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

                    using (var reader = new StreamReader(DirectoryName + FileItem))
                    {

                        while (!reader.EndOfStream)
                        {
                            var item = new Hotel();
                            var line = reader.ReadLine();
                            var values = line.Split(';');

                            item.CurrentExecutionDate = DateTime.ParseExact(values[0], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.WebSite = values[1];
                            item.SearchStartDate = DateTime.ParseExact(values[2], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.SearchEndDate = DateTime.ParseExact(values[3], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            item.CityName = values[4];
                            item.HotelName = values[5];
                            //item.Link = values[?];
                            item.Price = values[6];
                            item.Rating = values[7];
                            item.PaymentConditions = values[8];
                            item.Nights = values[9];
                            item.People = values[10];
                            //item.Html = values[?];
                            //item.WebSite = values[?];
                            //item.LastPrice = values[11];
                            //item.DateLastPrice = DateTime.ParseExact(values[12], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            //item.PriceDifferencePercentage = values[13];
                            //item.BiggestPrice = values[14];
                            //item.DateBiggestPrice = DateTime.ParseExact(values[15], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            //item.LowestPrice = values[16];
                            //item.DateLowestPrice = DateTime.ParseExact(values[17], "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                            //item.NumberSearches = int.Parse(values[18]);
                            //item.SumPrice = values[19];
                            //item.AveragePrice = values[20];
                            item.Link = values[21];

                            List.Add(item);
                        }
                    }
                }
                return List;
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to reading the Decolar csv file: {ex.Message}. ", ex);
                throw;
            }
        }
    }
}
