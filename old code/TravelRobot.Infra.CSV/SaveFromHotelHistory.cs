using Serilog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.File
{
    public class SaveFromHotelHistory : ISaveFromHotelHistory
    {
        private List<HotelHistory> _HotelHistoryList = new List<HotelHistory>();
        private const string _DirectoryHoteHistorylList = @"D:\Projetos\Viagem\HotelHistory\";

        private string HotelNameErro = "";
        private string CityNameErro = "";

        public SaveFromHotelHistory()
        {
            _HotelHistoryList = new List<HotelHistory>();
        }

        public void SetHotelList(List<HotelHistory> HotelHistoryList)
        {
            _HotelHistoryList = HotelHistoryList;
        }

        public void Salve()
        {

            bool isEmpty = (_HotelHistoryList.Count == 0 ? true : false);
            if (!isEmpty)
            {
                try
                {
                    var path = _DirectoryHoteHistorylList + "HotelHistory_" + DateTime.Now.ToString("yyyyMMdd") + ".csv";

                    using (var writer = new StreamWriter(path))
                    {

                        foreach (HotelHistory item in _HotelHistoryList)
                        {
                            var text = "";

                            HotelNameErro = item.HotelName;
                            CityNameErro = item.CityName;

                            text += item.CurrentExecutionDate.ToString("yyyy-MM-dd") + ";";
                            text += item.CityName + ";";
                            text += item.HotelName + ";";
                            text += item.Rating + ";";
                            text += item.LastPrice + ";";
                            text += ((item.DateLastPrice.HasValue) ? item.DateLastPrice.Value.ToString("yyyy-MM-dd") : "") + ";";
                            text += item.PriceDifferencePercentage + ";";
                            text += item.BiggestPrice + ";";
                            text += ((item.DateBiggestPrice.HasValue) ? item.DateBiggestPrice.Value.ToString("yyyy-MM-dd") : "") + ";";
                            text += item.LowestPrice + ";";
                            text += ((item.DateLowestPrice.HasValue) ? item.DateLowestPrice.Value.ToString("yyyy-MM-dd") : "") + ";";
                            text += item.NumberSearches + ";";
                            text += item.SumPrice + ";";
                            text += item.AveragePrice + ";";

                            writer.WriteLine(text);
                        }
                    }
                }
                catch (Exception ex)
                {
                    Log.Error($"The following error occurred when to writing the Hotels History's csv file, Hotel Name {HotelNameErro} - City Name {CityNameErro} : {ex.Message}. ", ex);
                }
            }
        }
    }
}
