using AngleSharp;
using AngleSharp.Html.Parser;
using Serilog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Formatters.Binary;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Domain.Layout;

namespace TravelRobot.Infra.DataExtraction.Booking
{
    public class SearchReviewsBooking : ISearchReviewsBooking
    {
        private List<Hotel> _Hotel;
        private SynchronizedCollection<GuestReviews> _GuestReviewsList;

        private string GuestReviews_Employees_searchText = "Funcionários";
        private string GuestReviews_Comfort_searchText = "Conforto";
        private string GuestReviews_Amenities_searchText = "Comodidades";
        private string GuestReviews_Cleaning_searchText = "Limpeza";
        private string GuestReviews_CostBenefit_searchText = "Custo-benefício";
        private string GuestReviews_Location_searchText = "Localização";

        private const long LimitValuePauseCounter = 2;

        private long TotalHotels;
        private long CounterThread;
        private long PauseCounterThread;
        private long AccountantWhoStoppedLimit;

        private CountdownEvent cte = new CountdownEvent(1);
        private CountdownEvent cteLimit = new CountdownEvent(1);

        private IBookingReviews _BookingReviews;
        private IParameter _Parameter;

        private SearchReviewsBookingLayout _SearchReviewsBookingLayout;

        public SearchReviewsBooking(IBookingReviews BookingReviews, IParameter Parameter)
        {
            _BookingReviews = BookingReviews;
            _Parameter = Parameter;
            _SearchReviewsBookingLayout = _Parameter.GetSearchReviewsBookingLayout();

            GuestReviews_Employees_searchText = _SearchReviewsBookingLayout.GuestReviews_Employees_searchText;
            GuestReviews_Comfort_searchText = _SearchReviewsBookingLayout.GuestReviews_Comfort_searchText;
            GuestReviews_Amenities_searchText = _SearchReviewsBookingLayout.GuestReviews_Amenities_searchText;
            GuestReviews_Cleaning_searchText = _SearchReviewsBookingLayout.GuestReviews_Cleaning_searchText;
            GuestReviews_CostBenefit_searchText = _SearchReviewsBookingLayout.GuestReviews_CostBenefit_searchText;
            GuestReviews_Location_searchText = _SearchReviewsBookingLayout.GuestReviews_Location_searchText;

            _Hotel = new List<Hotel>();
            _GuestReviewsList = new SynchronizedCollection<GuestReviews>();

            TotalHotels = 0;
            CounterThread = 0;
            PauseCounterThread = 0;
            AccountantWhoStoppedLimit = 0;
        }

        public void SetHotel(List<Hotel> InfHotel)
        {
            foreach (Hotel _InfHotelItem in InfHotel)
            {
                if (_Hotel.Where(T => T.HotelName == _InfHotelItem.HotelName && T.CityName == _InfHotelItem.CityName).Count() == 0)
                {
                    _Hotel.Add(new Hotel
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
                    TotalHotels++;
                }
            }
        }
        public void SetHotel(Hotel InfHotel)
        {
            _Hotel.Add(new Hotel { CurrentExecutionDate = InfHotel.CurrentExecutionDate, SearchStartDate = InfHotel.SearchStartDate, SearchEndDate = InfHotel.SearchEndDate, CityName = InfHotel.CityName, HotelName = InfHotel.HotelName, Link = InfHotel.Link, Price = InfHotel.Price,
                Rating = InfHotel.Rating, PaymentConditions = InfHotel.PaymentConditions, Nights = InfHotel.Nights, People = InfHotel.People, Html = InfHotel.Html, WebSite = InfHotel.WebSite,
                HotelAddress = InfHotel.HotelAddress, GuestReviews_Rating = InfHotel.GuestReviews_Rating, GuestReviews_Employees = InfHotel.GuestReviews_Employees,
                GuestReviews_Comfort = InfHotel.GuestReviews_Comfort, GuestReviews_Amenities = InfHotel.GuestReviews_Amenities, GuestReviews_Cleaning = InfHotel.GuestReviews_Cleaning, GuestReviews_CostBenefit = InfHotel.GuestReviews_CostBenefit,
                GuestReviews_Location = InfHotel.GuestReviews_Location, GuestReviews_WiFi = InfHotel.GuestReviews_WiFi, GuestReviews_NumberOfReviews = InfHotel.GuestReviews_NumberOfReviews
            });
            TotalHotels = 1;
        }

        public void BuildHTMLPage()
        {

            ParallelOptions options = new ParallelOptions();
            options.MaxDegreeOfParallelism = _SearchReviewsBookingLayout.CounterThread; //max threads

            Parallel.For(0, _Hotel.Count(), options, i => {
                CounterThread++;
                BuildEachHotel(_Hotel[i], CounterThread, _Hotel.Count());
            });

            //foreach (var HotelItem in _Hotel)
            //{
            //    //var reportThread = new Thread(() => ;
            //    //reportThread.Name = "Thread Hotel: " + HotelItem.HotelName.ToString();
            //    //cte.AddCount();
            //    //reportThread.Start();

            //    Task.Factory.StartNew(() =>
            //    {
            //        BuildEachHotel(HotelItem); 
            //        cte.AddCount();
            //        cte.Wait();
            //        cteLimit.AddCount();
            //        cteLimit.Wait();
            //    });

            //}

        }

        private void BuildEachHotel(Hotel HotelItem, long CurrentCounter, long TotalCounter)
        {
            try
            {
                Log.Information($"{CurrentCounter} to {TotalCounter}");
                string SearchText = HotelItem.HotelName + " " + HotelItem.CityName + " Booking";
                var HTMLAll = "";
                using (var GetHtml = (IBookingReviews)_BookingReviews.Clone())
                {
                    HTMLAll = ((IBookingReviews)_BookingReviews.Clone()).GetHtml(SearchText);
                }
                var config = Configuration.Default;
                var parser = new HtmlParser();
                var document = parser.ParseDocument(HTMLAll);
                
                var ListResultsDiv = document.All.Where(m => m.LocalName == _SearchReviewsBookingLayout.ListResultsDivLocalName && m.Id == _SearchReviewsBookingLayout.ListResultsDivID);

                foreach (var item in ListResultsDiv)
                {
                    var _GuestReviews = new GuestReviews();
                    var documentItem = parser.ParseDocument(item.InnerHtml);

                    _GuestReviews.CityName = HotelItem.CityName;
                    _GuestReviews.HotelName = HotelItem.HotelName;
                    _GuestReviews.HotelAddress = Regex.Replace(document.GetElementsByClassName(_SearchReviewsBookingLayout.HotelAddressClassName)[0].TextContent.Replace(System.Environment.NewLine, ""), @"\r\n?|\n", "");
                    _GuestReviews.GuestReviews_NumberOfReviews = documentItem.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_NumberOfReviewsClassName)[0].TextContent.Replace(_SearchReviewsBookingLayout.GuestReviews_NumberOfReviewsReplace, "").Replace(".", "").Replace(" · ", "");
                    _GuestReviews.GuestReviews_Rating = documentItem.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_RatingClassName)[0].TextContent;

                    var ListResults = documentItem.QuerySelectorAll(_SearchReviewsBookingLayout.ListResultsSelectors);

                    foreach (var item2 in ListResults)
                    {
                        var TypeGuestReviews = item2.GetElementsByClassName(_SearchReviewsBookingLayout.TypeGuestReviewsClassName)[0].TextContent.Trim();

                        if (TypeGuestReviews == GuestReviews_Employees_searchText)
                            _GuestReviews.GuestReviews_Employees = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_EmployeesClassName)[0].TextContent;
                        else if (TypeGuestReviews == GuestReviews_Comfort_searchText)
                            _GuestReviews.GuestReviews_Comfort = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_ComfortClassName)[0].TextContent;
                        else if (TypeGuestReviews == GuestReviews_Amenities_searchText)
                            _GuestReviews.GuestReviews_Amenities = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_AmenitiesClassName)[0].TextContent;
                        else if (TypeGuestReviews == GuestReviews_Cleaning_searchText)
                            _GuestReviews.GuestReviews_Cleaning = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_CleaningClassName)[0].TextContent;
                        else if (TypeGuestReviews == GuestReviews_CostBenefit_searchText)
                            _GuestReviews.GuestReviews_CostBenefit = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_CostBenefitClassName)[0].TextContent;
                        else if (TypeGuestReviews == GuestReviews_Location_searchText)
                            _GuestReviews.GuestReviews_Location = item2.GetElementsByClassName(_SearchReviewsBookingLayout.GuestReviews_LocationClassName)[0].TextContent;
                    }
                    _GuestReviewsList.Add(_GuestReviews);
                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying getting data at Booking by Hotel {HotelItem.HotelName} SearchReviewsBooking class: {ex.Message}. ", ex);
            }
        }

        public List<GuestReviews> GetGuestReviewslList()
        {
            var Result = new List<GuestReviews>();
            foreach (var item in _GuestReviewsList)
                Result.Add(new GuestReviews
                {
                    CityName = item.CityName,
                    HotelName = item.HotelName,
                    HotelAddress = item.HotelAddress,
                    GuestReviews_Rating = item.GuestReviews_Rating,
                    GuestReviews_Employees = item.GuestReviews_Employees,
                    GuestReviews_Comfort = item.GuestReviews_Comfort,
                    GuestReviews_Amenities = item.GuestReviews_Amenities,
                    GuestReviews_Cleaning = item.GuestReviews_Cleaning,
                    GuestReviews_CostBenefit = item.GuestReviews_CostBenefit,
                    GuestReviews_Location = item.GuestReviews_Location,
                    GuestReviews_WiFi = item.GuestReviews_WiFi,
                    GuestReviews_NumberOfReviews = item.GuestReviews_NumberOfReviews
                });
            return Result;
        }
    }
}
