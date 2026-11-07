using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Application
{

    public class DesignerHotelHistory : IDesignerHotelHistory
    {

        private IReadFileHotelHistory _ReadFileHotelHistory;

        public DesignerHotelHistory(IReadFileHotelHistory ReadFileHotelHistory)
        {
            _ReadFileHotelHistory = ReadFileHotelHistory;
        }

        public List<HotelHistory> CreatingHotelHistory(List<Hotel> HotelsList)
        {
            var HotelHistoryList = new List<HotelHistory>();
            var LastHotelHistoryList = _ReadFileHotelHistory.ReadLatestData();
            List<Hotel> clonedHotelsList = CreateClonedHoteList(HotelsList);
            var _HotelHistory = new HotelHistory();

            foreach (var HotelHistoryFor in LastHotelHistoryList)
            {
                if (HotelHistoryFor != null)
                {
                    _HotelHistory = new HotelHistory();
                    var HotelExistsInCurrentProcessing = clonedHotelsList.Where(T => T.HotelName == HotelHistoryFor.HotelName && T.CityName == HotelHistoryFor.CityName).Count() > 0 ? true : false;
                    var Hotel = HotelExistsInCurrentProcessing ? clonedHotelsList.Where(T => T.HotelName == HotelHistoryFor.HotelName && T.CityName == HotelHistoryFor.CityName).First() : new Hotel();
                    
                    _HotelHistory.CurrentExecutionDate = (HotelExistsInCurrentProcessing) ? Hotel.CurrentExecutionDate : HotelHistoryFor.CurrentExecutionDate;
                    _HotelHistory.CityName = HotelHistoryFor.CityName;
                    _HotelHistory.HotelName = HotelHistoryFor.HotelName;
                    _HotelHistory.Rating = HotelHistoryFor.Rating;
                    //_HotelHistory.LastPrice = (HotelExistsInCurrentProcessing) ? Hotel.LastPrice : HotelHistoryFor.LastPrice;
                    _HotelHistory.DateLastPrice = (HotelExistsInCurrentProcessing) ? Hotel.CurrentExecutionDate : HotelHistoryFor.DateLastPrice;

                    if (HotelExistsInCurrentProcessing)
                    {
                        var LastPriceDec = DecimalPriceTreatment(HotelHistoryFor.LastPrice);
                        //var PriceDec = DecimalPriceTreatment(Hotel.LastPrice);
                        var BiggestPriceDec = DecimalPriceTreatment(HotelHistoryFor.BiggestPrice);
                        var LowestPriceDec = DecimalPriceTreatment(HotelHistoryFor.LowestPrice);
                        var NumberSearchesLong = (long)Convert.ToDouble(HotelHistoryFor.NumberSearches);
                        var SumPriceDec = DecimalPriceTreatment(HotelHistoryFor.SumPrice);

                        //_HotelHistory.PriceDifferencePercentage = ((LastPriceDec / PriceDec - 1) * 100).ToString();
                        //_HotelHistory.BiggestPrice = PriceDec > BiggestPriceDec ? Hotel.Price : _HotelHistory.BiggestPrice;
                        //_HotelHistory.DateBiggestPrice = PriceDec > BiggestPriceDec ? Hotel.CurrentExecutionDate : _HotelHistory.DateBiggestPrice;
                        //_HotelHistory.LowestPrice = PriceDec < LowestPriceDec ? Hotel.Price : _HotelHistory.LowestPrice;
                        //_HotelHistory.DateLowestPrice = PriceDec < LowestPriceDec ? Hotel.CurrentExecutionDate : _HotelHistory.DateLowestPrice;
                        //_HotelHistory.NumberSearches = (NumberSearchesLong + 1);
                        //_HotelHistory.SumPrice = (SumPriceDec + PriceDec).ToString();
                        //_HotelHistory.AveragePrice = ((SumPriceDec + PriceDec) / (NumberSearchesLong + 1)).ToString();
                    }
                    else
                    {
                        _HotelHistory.PriceDifferencePercentage = HotelHistoryFor.PriceDifferencePercentage;
                        _HotelHistory.BiggestPrice = HotelHistoryFor.BiggestPrice;
                        _HotelHistory.DateBiggestPrice = HotelHistoryFor.DateBiggestPrice;
                        _HotelHistory.LowestPrice = HotelHistoryFor.LowestPrice;
                        _HotelHistory.DateLowestPrice = HotelHistoryFor.DateLowestPrice;
                        _HotelHistory.NumberSearches = HotelHistoryFor.NumberSearches;
                        _HotelHistory.SumPrice = HotelHistoryFor.SumPrice;
                        _HotelHistory.AveragePrice = HotelHistoryFor.AveragePrice;
                    }

                    HotelHistoryList.Add(_HotelHistory);
                    clonedHotelsList.Remove(Hotel);
                }
            }

            foreach (var HotelFor in clonedHotelsList)
            {
                _HotelHistory = new HotelHistory();

                _HotelHistory.CurrentExecutionDate = HotelFor.CurrentExecutionDate;
                _HotelHistory.CityName = HotelFor.CityName;
                _HotelHistory.HotelName = HotelFor.HotelName;
                _HotelHistory.Rating = HotelFor.Rating;
                _HotelHistory.LastPrice = HotelFor.Price;
                _HotelHistory.DateLastPrice = HotelFor.CurrentExecutionDate;
                //_HotelHistory.PriceDifferencePercentage = HotelFor.PriceDifferencePercentage;
                //_HotelHistory.BiggestPrice = HotelFor.BiggestPrice;
                //_HotelHistory.DateBiggestPrice = HotelFor.DateBiggestPrice;
                //_HotelHistory.LowestPrice = HotelFor.LowestPrice;
                //_HotelHistory.DateLowestPrice = HotelFor.DateLowestPrice;
                //_HotelHistory.NumberSearches = HotelFor.NumberSearches;
                //_HotelHistory.SumPrice = HotelFor.SumPrice;
                //_HotelHistory.AveragePrice = HotelFor.AveragePrice;

                HotelHistoryList.Add(_HotelHistory);

            }

            return HotelHistoryList;

        }

        private List<Hotel> CreateClonedHoteList(List<Hotel> HotelsList)
        {
            List<Hotel> clonedHotelsList = new List<Hotel>();
            HotelsList.ForEach((item) =>
            {
                var NewHotel = new Hotel();
                NewHotel.CurrentExecutionDate = item.CurrentExecutionDate;
                NewHotel.SearchStartDate = item.SearchStartDate;
                NewHotel.SearchEndDate = item.SearchEndDate;
                NewHotel.CityName = item.CityName;
                NewHotel.HotelName = item.HotelName;
                NewHotel.Link = item.Link;
                NewHotel.Price = item.Price;
                NewHotel.Rating = item.Rating;
                NewHotel.PaymentConditions = item.PaymentConditions;
                NewHotel.Nights = item.Nights;
                NewHotel.People = item.People;
                NewHotel.Html = item.Html;
                NewHotel.WebSite = item.WebSite;
                //NewHotel.LastPrice = item.LastPrice;
                //NewHotel.DateLastPrice = item.DateLastPrice;
                //NewHotel.PriceDifferencePercentage = item.PriceDifferencePercentage;
                //NewHotel.BiggestPrice = item.BiggestPrice;
                //NewHotel.DateBiggestPrice = item.DateBiggestPrice;
                //NewHotel.LowestPrice = item.LowestPrice;
                //NewHotel.DateLowestPrice = item.DateLowestPrice;
                //NewHotel.NumberSearches = item.NumberSearches;
                //NewHotel.SumPrice = item.SumPrice;
                //NewHotel.AveragePrice = item.AveragePrice;

                clonedHotelsList.Add(NewHotel);
            });
            return clonedHotelsList;
        }

        private static decimal DecimalPriceTreatment(string value)
        {
            decimal valueOut;
            return (Decimal.TryParse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), out valueOut)) ? Decimal.Parse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
        }
    }
}
