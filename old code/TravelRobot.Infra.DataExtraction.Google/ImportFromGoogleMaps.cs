using AngleSharp;
using AngleSharp.Html.Parser;
using Serilog;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Domain.Layout;

namespace TravelRobot.Infra.DataExtraction.Google
{
    public class ImportFromGoogleMaps : IImportFromGoogleMaps
    {
        private List<Hotel> _PastHotelsList = new List<Hotel>();
        private SynchronizedCollection<DistanceBetween> _DistanceBetweenList;

        private IGoogleMaps _GoogleMaps;
        private IParameter _Parameter;

        private SearchImportFromGoogleMapsLayout _SearchImportFromGoogleMapsLayout;

        private long CounterThread;

        public ImportFromGoogleMaps(IGoogleMaps GoogleMaps, IParameter Parameter)
        {
            _GoogleMaps = GoogleMaps;
            _DistanceBetweenList = new SynchronizedCollection<DistanceBetween>();
            _Parameter = Parameter;

            _SearchImportFromGoogleMapsLayout = _Parameter.GetSearchImportFromGoogleMapsLayout();
        }

        public void SetHotel(List<Hotel> InfHotel)
        {
            foreach (Hotel _InfHotelItem in InfHotel)
            {
                if (_PastHotelsList.Where(T => T.CityName == _InfHotelItem.CityName && T.HotelName == _InfHotelItem.HotelName).Count() == 0)
                {
                    _PastHotelsList.Add(new Hotel
                    {
                        CurrentExecutionDate = _InfHotelItem.CurrentExecutionDate,
                        SearchStartDate = _InfHotelItem.SearchStartDate,
                        SearchEndDate = _InfHotelItem.SearchEndDate,
                        CityName = _InfHotelItem.CityName,
                        HotelName = _InfHotelItem.HotelName,
                        Link = _InfHotelItem.Link,
                        Price = _InfHotelItem.Price,
                        Rating = _InfHotelItem.Rating,
                        PaymentConditions = _InfHotelItem.PaymentConditions,
                        Nights = _InfHotelItem.Nights,
                        People = _InfHotelItem.People,
                        Html = _InfHotelItem.Html,
                        WebSite = _InfHotelItem.WebSite,
                        HotelAddress = _InfHotelItem.HotelAddress,
                        GuestReviews_Rating = _InfHotelItem.GuestReviews_Rating,
                        GuestReviews_Employees = _InfHotelItem.GuestReviews_Employees,
                        GuestReviews_Comfort = _InfHotelItem.GuestReviews_Comfort,
                        GuestReviews_Amenities = _InfHotelItem.GuestReviews_Amenities,
                        GuestReviews_Cleaning = _InfHotelItem.GuestReviews_Cleaning,
                        GuestReviews_CostBenefit = _InfHotelItem.GuestReviews_CostBenefit,
                        GuestReviews_Location = _InfHotelItem.GuestReviews_Location,
                        GuestReviews_WiFi = _InfHotelItem.GuestReviews_WiFi,
                        GuestReviews_NumberOfReviews = _InfHotelItem.GuestReviews_NumberOfReviews
                    });
                }
                
            }
        }

        public void BuildHTMLPage(List<HotelSearchSettingParameters> ReferencePointA)
        {
            try
            {
                ParallelOptions options = new ParallelOptions();
                options.MaxDegreeOfParallelism = 4; //max threads

                Parallel.For(0, _PastHotelsList.Count(), options, i => {
                    CounterThread++;
                    GetDistanceEachHotel(ReferencePointA, _PastHotelsList[i], CounterThread, _PastHotelsList.Count());
                });

            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying getting data from Google Maps: {ex.Message}. ", ex);
            }
        }

        private void GetDistanceEachHotel(List<HotelSearchSettingParameters> ReferencePointA, Hotel _Hotel, long CurrentCounter, long TotalCounter)
        {
            try
            {
                Log.Information($"{CurrentCounter} to {TotalCounter}");

                var HTMLAll = ((IGoogleMaps)_GoogleMaps.Clone()).GetHtml(_Hotel.HotelAddress, ReferencePointA.Where(T => T.CityName == _Hotel.CityName).First().ReferencePointA);

                var config = Configuration.Default;
                var parser = new HtmlParser();
                var document = parser.ParseDocument(HTMLAll);

                var ItemDistanceBetween = new DistanceBetween();

                double _Km = 0;
                var stringKMs = document.GetElementsByClassName(_SearchImportFromGoogleMapsLayout.stringKMs_searchText)[0].TextContent;

                if (stringKMs.IndexOf(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfMilhas_searchText) > 0)
                    _Km = (double.Parse(stringKMs.Replace(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfMilhas_searchText, "")) / 0.65);
                else if (stringKMs.IndexOf(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfMilhas_searchText) > 0)
                    _Km = (double.Parse(stringKMs.Replace(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfMilhas_searchText, "")) / 0.65);
                else if (stringKMs.IndexOf(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfKm_searchText) > 0)
                    _Km = double.Parse(stringKMs.Replace(_SearchImportFromGoogleMapsLayout.stringKMsIndexOfKm_searchText, ""));


                ItemDistanceBetween.HotelName = _Hotel.HotelName;
                ItemDistanceBetween.CityName = _Hotel.CityName;
                ItemDistanceBetween.DistanceBetweenKM = _Km.ToString();

                _DistanceBetweenList.Add(ItemDistanceBetween);
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying getting Distance by from Google Maps - Hotel {_Hotel.HotelName}: {ex.Message}. ", ex);
            }
        }

        public List<DistanceBetween> GetListDistanceBetween()
        {
            var Result = new List<DistanceBetween>();
            foreach (var item in _DistanceBetweenList)
                Result.Add(new DistanceBetween
                {
                    CityName = item.CityName,
                    HotelName = item.HotelName,
                    DistanceBetweenKM = item.DistanceBetweenKM
                });
            return Result;
        }

    }
}
