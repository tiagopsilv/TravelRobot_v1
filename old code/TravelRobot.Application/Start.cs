using Serilog;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Enums;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Application
{
    public class Start : IStart
    {

        private IImportFromDecolarWebSite _ImportFromDecolarWebSite;
        private IURLDecolar _URLDecolar;
        private IImportFromSmilesWebSite _ImportFromSmilesWebSite;
        private ISendEmail _SendEmail;
        private IReadFileDecolar _ReadFileDecolar;
        private IHtmlSearchEnginePage _HtmlSearchEnginePage;
        private ISaveFromHotesWebSite _SaveFromHotesWebSite;
        private IDesignerHotelHistory _DesignerHotelHistory;
        private ISaveFromHotelHistory _SaveFromHotelHistory;
        private IImportFromGoogleWebSite _ImportFromGoogleWebSite;
        private ISearchDateCityRules _SearchDateCityRules;
        private ISearchReviewsBooking _SearchReviewsBooking;
        private IImportFromGoogleMaps _ImportFromGoogleMaps;
        private ISaveFactory _SaveFactory;

        public Start(IImportFromDecolarWebSite ImportFromDecolarWebSite, IURLDecolar URLDecolar, IImportFromSmilesWebSite ImportFromSmilesWebSite, ISendEmail SendEmail, IReadFileDecolar ReadFileDecolar, IHtmlSearchEnginePage HtmlSearchEnginePage, ISaveFromHotesWebSite SaveFromHotesWebSite, IDesignerHotelHistory DesignerHotelHistory, ISaveFromHotelHistory SaveFromHotelHistory, IImportFromGoogleWebSite ImportFromGoogleWebSite, ISearchDateCityRules SearchDateCityRules, ISearchReviewsBooking SearchReviewsBooking, IImportFromGoogleMaps ImportFromGoogleMaps, ISaveFactory SaveFactory)
        {
            _ImportFromDecolarWebSite = ImportFromDecolarWebSite;
            _URLDecolar = URLDecolar;
            _ImportFromSmilesWebSite = ImportFromSmilesWebSite;
            _SendEmail = SendEmail;
            _ReadFileDecolar = ReadFileDecolar;
            _HtmlSearchEnginePage = HtmlSearchEnginePage;
            _SaveFromHotesWebSite = SaveFromHotesWebSite;
            _DesignerHotelHistory = DesignerHotelHistory;
            _SaveFromHotelHistory = SaveFromHotelHistory;
            _ImportFromGoogleWebSite = ImportFromGoogleWebSite;
            _SearchDateCityRules = SearchDateCityRules;
            _SearchReviewsBooking = SearchReviewsBooking;
            _ImportFromGoogleMaps = ImportFromGoogleMaps;
            _SaveFactory = SaveFactory;
        }

        public void Main()
        {
            try
            {
                var ProcessingStartDate = DateTime.Now;
                var ProcessingTime = DateTime.Now - ProcessingStartDate;

                Log.Information("Start of TravelRobot processing {0}", DateTime.Now.ToString());

                Log.Information("Step 1 - Get Rules Hotel Search from Json File");
                var HotelSearchSettingRules = _SearchDateCityRules.GetListSearch();


                //var test = new List<Hotel>();
                //test.Add(new Hotel { CityName = "NovaYork", HotelName = "Washington Jefferson", HotelAddress = "318 W 51st St, New York, NY 10019, Estados Unidos" });
                //test.Add(new Hotel { CityName = "NovaYork", HotelName = "Four Points by Sheraton Manhattan Midtown West", HotelAddress = "444 10th Avenue Entrance On Corner Of 35th St, 10th Ave, New York, NY 10001, Estados Unidos" });
                ////test.Add(new Hotel { CityName = "NovaYork", HotelName = "OYO Times Square" });

                //_ImportFromGoogleMaps.SetHotel(test);
                //_ImportFromGoogleMaps.BuildHTMLPage(HotelSearchSettingRules);
                //var test2 = _ImportFromGoogleMaps.GetListDistanceBetween();


                Log.Information("Step 2 - Listing Hotels");
                //var HotelsFromLastImport = _ReadFileDecolar.ReadLatestData();

                Log.Information("Step 3 - Setting Hotel List from Google");
                foreach (var Hotel in HotelSearchSettingRules)
                    _ImportFromGoogleWebSite.SetHotelList(Hotel);

                Log.Information("Step 4 - Getting the Hotels List From Google");
                var HolesListGoogle = _ImportFromGoogleWebSite.GetHotelList();

                Log.Information("Step 5 - Setting Frequent Flyer List");
                _ImportFromSmilesWebSite.SetFrequentFlyerList();

                Log.Information("Step 6 - Getting Frequent Flyer List");
                var FrequentFlyerList = _ImportFromSmilesWebSite.GetHotelList();

                Log.Information("Step 7 - Setting to Save Frequent Flyer List");
                var SavaSmilesWebSite = _SaveFactory.BuildSaveSmilesWebSite();
                SavaSmilesWebSite.SetList(FrequentFlyerList);

                Log.Information("Step 8 - Writing Frequent Flyers List");
                SavaSmilesWebSite.Save();

                Log.Information("Step 9 - Setting Hotel List");
                foreach (var Hotel in HotelSearchSettingRules)
                    _ImportFromDecolarWebSite.SetHotelList(Hotel);

                Log.Information("Step 10 - Getting the Hotels List");
                var HolesListDecolar = _ImportFromDecolarWebSite.GetHotelList();

                var HolesList = HolesListDecolar.Union(HolesListGoogle).ToList();

                Log.Information("Step 10 - Getting Guest Reviews From Booking");
                _SearchReviewsBooking.SetHotel(HolesList);
                _SearchReviewsBooking.BuildHTMLPage();
                var GuestReviewslList = _SearchReviewsBooking.GetGuestReviewslList();

                Log.Information("Step 11 - Getting the distance from each hotel to the point");
                _ImportFromGoogleMaps.SetHotel(HolesList);
                _ImportFromGoogleMaps.BuildHTMLPage(HotelSearchSettingRules);
                var DistanceFromEachHotelToThePoint = _ImportFromGoogleMaps.GetListDistanceBetween();

                foreach (var Item in HolesList)
                {
                    var GuestReviewsItem = GuestReviewslList.Where(T => T.HotelName == Item.HotelName && T.CityName == Item.CityName).FirstOrDefault();
                    var DistanceFromEachHotelToThePointItem = DistanceFromEachHotelToThePoint.Where(T => T.HotelName == Item.HotelName && T.CityName == Item.CityName).FirstOrDefault();

                    if (GuestReviewsItem != null)
                    {
                        if (Item.HotelAddress.Length <= 0)
                            Item.HotelAddress = GuestReviewsItem.HotelAddress;
                        Item.GuestReviews_Rating = GuestReviewsItem.GuestReviews_Rating;
                        Item.GuestReviews_Amenities = GuestReviewsItem.GuestReviews_Amenities;
                        Item.GuestReviews_Cleaning = GuestReviewsItem.GuestReviews_Cleaning;
                        Item.GuestReviews_Comfort = GuestReviewsItem.GuestReviews_Comfort;
                        Item.GuestReviews_CostBenefit = GuestReviewsItem.GuestReviews_CostBenefit;
                        Item.GuestReviews_Employees = GuestReviewsItem.GuestReviews_Employees;
                        Item.GuestReviews_Location = GuestReviewsItem.GuestReviews_Location;
                        Item.GuestReviews_NumberOfReviews = GuestReviewsItem.GuestReviews_NumberOfReviews;
                        Item.GuestReviews_WiFi = GuestReviewsItem.GuestReviews_WiFi;
                    }
                    if (DistanceFromEachHotelToThePointItem != null)
                        Item.DistanceBetweenKM = DistanceFromEachHotelToThePointItem.DistanceBetweenKM;
                }

                Log.Information("Step 11 - Setting to Save Hotels List");
                var SavaHotesWebSite = _SaveFactory.BuildSaveHotesWebSite();
                SavaHotesWebSite.SetList(HolesList);

                Log.Information("Step 12 - Writing Hotels List");
                SavaHotesWebSite.Save();

                //Log.Information("Step 13 - Creating Hotel History");
                //var HotelHistoryList = _DesignerHotelHistory.CreatingHotelHistory(HolesList);

                //Log.Information("Step 14 - Setting to Save Hotels History List");
                //_SaveFromHotelHistory.SetHotelList(HotelHistoryList);

                //Log.Information("Step 15 - Writing Hotels History List");
                //_SaveFromHotelHistory.Salve();

                ProcessingTime = DateTime.Now - ProcessingStartDate;

                Log.Information($"Processing Summary: {Environment.NewLine} " +
                                $"Count of Frequent Flyer: {FrequentFlyerList.Count} {Environment.NewLine} " +
                                $"Count of Hotels: {HolesList.Count} {Environment.NewLine} " + 
                                $"Processing time: {(int)ProcessingTime.TotalHours + ProcessingTime.ToString(@"\:mm\:ss")}.");

                Log.Information("The end");
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying to run the TravelRobot: {ex.Message}. ", ex);
                throw;
            }

        }
    }
}
