using AngleSharp;
using AngleSharp.Html.Parser;
using Newtonsoft.Json;
using Serilog;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.DataExtraction.Google
{
    public class ImportFromGoogleWebSite : IImportFromGoogleWebSite
    {
        private SynchronizedCollection<Hotel> HotelList = new SynchronizedCollection<Hotel>();

        private IGoogleHotels _GoogleHotels;
        private string _ErrorLink;
        private string _ErrorWebSite;
        private long CounterThread;

        private List<Hotel> _PastHotelsList = new List<Hotel>();

        public ImportFromGoogleWebSite(IGoogleHotels GoogleHotels)
        {
            _GoogleHotels = GoogleHotels;
        }

        public List<Hotel> GetHotelList()
        {
            var Result = new List<Hotel>();
            foreach (var item in HotelList)
                Result.Add(new Hotel
                {
                CurrentExecutionDate = item.CurrentExecutionDate,
                SearchStartDate = item.SearchStartDate,
                SearchEndDate = item.SearchEndDate,
                CityName = item.CityName,
                HotelName= item.HotelName,
                Link = item.Link,
                Price = item.Price,
                Rating = item.Rating,
                PaymentConditions = item.PaymentConditions,
                Nights = item.Nights,
                People = item.People,
                Html = item.Html,
                WebSite= item.WebSite,
                HotelAddress= item.HotelAddress,
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

        public void SetPastHotelsList(List<Hotel> PastHotelsList)
        {
            _PastHotelsList = PastHotelsList;
        }

        public void SetHotelList(HotelSearchSettingParameters HotelSearchSettingRules)
        {
            try
            {
                var HotelSearchList = new List<GoogleHotelSearch>();
                Log.Information($"Start: { ((DateTime)HotelSearchSettingRules.Start).ToString("dd/MM/yyyy") }  End: { ((DateTime)HotelSearchSettingRules.End).ToString("dd/MM/yyyy") } City: {HotelSearchSettingRules.CityName.ToString()} ");

                var URLList = _GoogleHotels.GetHotels(HotelSearchSettingRules.TextForSearch, HotelSearchSettingRules.Start.Value, HotelSearchSettingRules.End.Value);

                if (URLList.Count > 0)
                {

                    foreach (var Item in URLList)
                    {
                        var parser = new HtmlParser();
                        var document = parser.ParseDocument(Item);

                        var ListResults = document.QuerySelectorAll("div.pjDrrc");

                        foreach (var ItemURLs in ListResults)
                        {
                            var documentItem = parser.ParseDocument(ItemURLs.InnerHtml);

                            var HotelFound = new GoogleHotelSearch();
                            HotelFound.StartDate = HotelSearchSettingRules.Start.Value.ToString("dd/MM/yyyy");
                            HotelFound.EndDate = HotelSearchSettingRules.End.Value.ToString("dd/MM/yyyy");
                            HotelFound.CityName = HotelSearchSettingRules.CityName;
                            HotelFound.WebSiteURL = @"https://www.google.com.br" + documentItem.GetElementsByClassName("aS3xV lRagtb xl0RMe")[0].GetAttribute("href");
                            HotelFound.HotelName = documentItem.GetElementsByClassName("BgYkof ogfYpf ykx2he")[0].TextContent.Trim();
                            if (documentItem.GetElementsByClassName("KFi5wf lA0BZ").Length > 0)
                                HotelFound.Rating = Regex.Match(documentItem.GetElementsByClassName("KFi5wf lA0BZ")[0].TextContent, @"[0-9]+(\.[0-9]+)?").Value;
                            HotelSearchList.Add(HotelFound);
                        }
                    }

                    ParallelOptions options = new ParallelOptions();
                    options.MaxDegreeOfParallelism = 7; //max threads

                    Parallel.For(0, HotelSearchList.Count(), options, i => {
                        _ErrorLink = HotelSearchList[i].WebSiteURL;
                        CounterThread++;
                        GetListHotelsPrice(HotelSearchSettingRules, HotelSearchList[i], CounterThread, HotelSearchList.Count());
                    });

                    //foreach (var PageHotel in HotelSearchList)
                    //{
                    //    _ErrorLink = PageHotel.WebSiteURL;
                    //    GetListHotelsPrice(HotelSearchSettingRules, PageHotel);
                    //}
                }
            
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying setting the list of Hotels from ImportFromGoogleWebSite class: {ex.Message}. Page Link: {_ErrorLink} ", ex);
            }
        }

        private void GetListHotelsPrice(HotelSearchSettingParameters HotelSearchSettingRules, GoogleHotelSearch PageHotel, long CurrentCounter, long TotalCounter)
        {
            Log.Information($"{CurrentCounter} to {TotalCounter}");
            var Htmls = ((IGoogleHotels)_GoogleHotels.Clone()).GetHotelsPrices(PageHotel.WebSiteURL);
            var parser = new HtmlParser();
            if (Htmls.Where(T => T.Tag == "HotelsPrices").Count() > 0)
            {
                var document = parser.ParseDocument(Htmls.Where(T => T.Tag == "HotelsPrices").First().Return.ToString());
                var ListResults = document.QuerySelectorAll("div.ADs2Tc");

                foreach (var item in ListResults)
                {
                    if (item.InnerHtml.Length > 0)
                    {
                        var documentItem = parser.ParseDocument(item.InnerHtml);
                        try
                        {
                            if (documentItem.GetElementsByClassName("nDkDDb").Length > 0)
                            {
                                var _Hotel = new Hotel();

                                _Hotel.CityName = HotelSearchSettingRules.CityName;

                                _Hotel.CurrentExecutionDate = DateTime.Now;

                                _Hotel.HotelAddress = GetAdress(Htmls.Where(T => T.Tag == "GeneralInformation").First().Return.ToString(), PageHotel.HotelName);

                                _Hotel.SearchStartDate = HotelSearchSettingRules.Start;

                                _Hotel.SearchEndDate = HotelSearchSettingRules.End;

                                _Hotel.HotelName = PageHotel.HotelName;

                                if (documentItem.GetElementsByClassName("NiGhzc").Length > 0)
                                {
                                    _ErrorWebSite = documentItem.GetElementsByClassName("NiGhzc")[0].TextContent;
                                    _Hotel.WebSite = documentItem.GetElementsByClassName("NiGhzc")[0].TextContent.Trim();
                                }

                                _Hotel.Link = FormatLinkPage(PageHotel, documentItem);

                                _Hotel.Html = item.InnerHtml;

                                if (PageHotel.Rating != null)
                                    if (PageHotel.Rating.Length > 0)
                                        _Hotel.Rating = PageHotel.Rating;

                                //_Hotel.HotelName = documentItem.GetElementsByClassName("accommodation-name -eva-3-ellipsis")[0].TextContent;

                                //Log.Information($"Processing hotel {_Hotel.HotelName} from {_Hotel.CityName} - Decolar website.");

                                //if (documentItem.GetElementsByClassName("tooltip-text -eva-3-mb-xsm").Length > 0)
                                //    _Hotel.Rating = Regex.Match(documentItem.GetElementsByClassName("tooltip-text -eva-3-mb-xsm")[0].TextContent, @"[0-9]+(\.[0-9]+)?").Value;

                                //if (documentItem.GetElementsByClassName("eva-3-p -eva-3-mt-xsm").Length > 0)
                                //    _Hotel.PaymentConditions = documentItem.GetElementsByClassName("eva-3-p -eva-3-mt-xsm")[0].TextContent;

                                //if (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message").Length > 0)
                                //    //_Hotel.Nights = (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.Substring(0, documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.IndexOf(" noite,", 0)));

                                //    if (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message").Length > 0)
                                //        _Hotel.People = (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.Substring(documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.IndexOf(", ", 0) + 2).Replace(" pessoas", ""));

                                if (documentItem.GetElementsByClassName("nDkDDb").Length > 0)
                                    _Hotel.Price = (documentItem.GetElementsByClassName("nDkDDb")[0].TextContent.Replace("R$", "").Trim());

                                if (_Hotel.Price != null && _Hotel.WebSite != null && _Hotel.Link != null)
                                    HotelList.Add(_Hotel);
                            }
                        }
                        catch (Exception ex)
                        {
                            Log.Error($"The Hotel {PageHotel.HotelName} WebSite {_ErrorWebSite}: {ex.Message}. Page Link: {_ErrorLink} ", ex);
                        }
                    }
                }
            }
        }

        private string FormatLinkPage(GoogleHotelSearch PageHotel, AngleSharp.Html.Dom.IHtmlDocument documentItem)
        {
            var Result = "";
            try
            {
                if (documentItem.GetElementsByClassName("hUGVEe cTvP0c").Length > 0)
                {
                    var _LinkT = documentItem.GetElementsByClassName("hUGVEe cTvP0c")[0].GetAttribute("href");
                    var ValIdx = 0;
                    if (_LinkT.IndexOf(@"https://") > 0)
                        ValIdx = _LinkT.IndexOf(@"https://");
                    else if (_LinkT.IndexOf(@"https://") > 0)
                        ValIdx = _LinkT.IndexOf(@"http://");

                    Result = _LinkT.Substring(ValIdx);
                }
            }
            catch (Exception ex)
            {
                Log.Error($"Erro to create URL to Link - Hotel {PageHotel.HotelName} WebSite {_ErrorWebSite}: {ex.Message}. Page Link: {_ErrorLink} ", ex);
            }
            return Result;
        }

        private string GetAdress(string Html, string HotelName)
        {
            var Result = "";
            try
            {
                var parser = new HtmlParser();
                var document = parser.ParseDocument(Html);
                var ListResults = document.QuerySelectorAll("div.K4nuhf");

                Result = ListResults.Where(T => T.ClassName == "K4nuhf").First().GetElementsByClassName("CFH2De").First().TextContent;
            }
            catch (Exception ex)
            {
                Log.Error($"The to try Get Adress - Hotel Name {HotelName}: ", ex);
            }
            return Result;
        }

        private static decimal DecimalPriceTreatment(string value)
        {
            decimal valueOut;
            return (Decimal.TryParse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), out valueOut)) ? Decimal.Parse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
        }
        public static string TrimSpacesBetweenString(string s)
        {
            var mystring = s.Split(new string[] { " " }, StringSplitOptions.None);
            string result = string.Empty;
            foreach (var mstr in mystring)
            {
                var ss = mstr.Trim();
                if (!string.IsNullOrEmpty(ss))
                {
                    result = result + ss + " ";
                }
            }
            return result.Trim();

        }

        //private List<DatesRange> GetDateListSearch(HotelSearch Search, DateTime? StartDate, DateTime? EndDate)
        //{
        //    var DateListSearch = new List<DatesRange>();
        //    var RangeSearchType = Search.RangeSearchType;
        //    var Date = StartDate;

        //    if (RangeSearchType == "Week")
        //    {
        //        while (Date < EndDate)
        //        {
        //            DateTime? DataStartWeek = Date;
        //            DateTime? nextSunday = Date.Value.AddDays((((int)DayOfWeek.Sunday - (int)Date.Value.DayOfWeek + 7) % 7));
        //            DateListSearch.Add(new DatesRange { Start = DataStartWeek, End = nextSunday });
        //            Date = nextSunday.Value.AddDays(1);
        //        }
        //    }
        //    return DateListSearch;
        //}

        //private static DateTime? GetStartDate(HotelSearch Search)
        //{
        //    DateTime? StartDate = null;
        //    switch (Search.StartDate)
        //    {
        //        case "CurrentDate":
        //            StartDate = DateTime.Now;
        //            break;
        //        default:
        //            break;
        //    }

        //    return StartDate;
        //}

        //private static DateTime? GetEndDate(HotelSearch Search)
        //{
        //    DateTime? GetEndDate = null;
        //    switch (Search.EndDate)
        //    {
        //        case "EndOfYear":
        //            GetEndDate = new DateTime(DateTime.Now.Year, 12, 31);
        //            break;
        //        case "EndOfMonth":
        //            GetEndDate = new DateTime(DateTime.Now.Year, DateTime.Now.Month, DateTime.DaysInMonth(DateTime.Now.Year, DateTime.Now.Month));
        //            break;
        //        default:
        //            break;
        //    }

        //    return GetEndDate;
        //}

        //private List<HotelSearch> GetHotelSearch()
        //{
        //    string filePath = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, @"..\..\..\")) + @"ConfigHotelSearch.json";
        //    string _countryJson = File.ReadAllText(filePath);
        //    return JsonConvert.DeserializeObject<List<HotelSearch>>(_countryJson);
        //}
    }
}
