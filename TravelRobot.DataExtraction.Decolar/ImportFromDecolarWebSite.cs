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
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Infra.Selenium;

namespace TravelRobot.Infra.DataExtraction.Decolar
{
    public class ImportFromDecolarWebSite : IImportFromDecolarWebSite
    {
        private List<Hotel> HotelList = new List<Hotel>();
        private string currentURL;
        private int CountPage = 1;

        public List<Hotel> GetHotelList()
        {
            return HotelList;
        }

        public void SetHotelList(HotelSearchSettingParameters HotelSearchSettingRules)
        {
            try
            {

                Log.Information($"Start: { ((DateTime)HotelSearchSettingRules.Start).ToString("dd/MM/yyyy") } {Environment.NewLine}  End: { ((DateTime)HotelSearchSettingRules.End).ToString("dd/MM/yyyy") }.");

                HtmlSearchEnginePage Html = new HtmlSearchEnginePage();

                SetConfigURL(HotelSearchSettingRules, HotelSearchSettingRules.Start, HotelSearchSettingRules.End);

                var HTMLAll = Html.GetHtml(currentURL + "&page=" + CountPage.ToString());

                var config = Configuration.Default;
                var parser = new HtmlParser();
                var document = parser.ParseDocument(HTMLAll);
                var ListResults = document.QuerySelectorAll("div.results-cluster-container");

                foreach (var item in ListResults)
                {
                    var documentItem = parser.ParseDocument(item.InnerHtml);
                    if (documentItem.GetElementsByClassName("accommodation-name -eva-3-ellipsis").Length > 0)
                    {
                        var _Hotel = new Hotel();

                        _Hotel.CityName = HotelSearchSettingRules.CityName.ToString();

                        _Hotel.CurrentExecutionDate = DateTime.Now;

                        _Hotel.SearchStartDate = HotelSearchSettingRules.Start;

                        _Hotel.SearchEndDate = HotelSearchSettingRules.End;

                        _Hotel.WebSite = "Decolar";

                        _Hotel.Html = item.InnerHtml;

                        _Hotel.HotelName = documentItem.GetElementsByClassName("accommodation-name -eva-3-ellipsis")[0].TextContent;

                        Log.Information($"Processing hotel {_Hotel.HotelName} from {_Hotel.CityName} - Decolar website.");

                        if (documentItem.GetElementsByClassName("tooltip-text -eva-3-mb-xsm").Length > 0)
                            _Hotel.Rating = Regex.Match(documentItem.GetElementsByClassName("tooltip-text -eva-3-mb-xsm")[0].TextContent, @"[0-9]+(\.[0-9]+)?").Value;

                        if (documentItem.GetElementsByClassName("eva-3-p -eva-3-mt-xsm").Length > 0)
                            _Hotel.PaymentConditions = documentItem.GetElementsByClassName("eva-3-p -eva-3-mt-xsm")[0].TextContent;

                        if (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message").Length > 0)
                            //_Hotel.Nights = (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.Substring(0, documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.IndexOf(" noite,", 0)));

                            if (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message").Length > 0)
                                _Hotel.People = (documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.Substring(documentItem.GetElementsByClassName("eva-3-p -eva-3-tc-gray-0 first-message")[0].TextContent.IndexOf(", ", 0) + 2).Replace(" pessoas", ""));

                        _Hotel.Price = (documentItem.GetElementsByClassName("main-value")[0].TextContent);

                        //if (PastHotelsList.Where(T => T.CityName == Search.CityName && T.HotelName == _Hotel.HotelName).Count() >= 1)
                        //{
                        //    var PastHotel = PastHotelsList.Where(T => T.CityName == Search.CityName && T.HotelName == _Hotel.HotelName).First();
                        //    decimal value;

                        //    var LastPriceDec = (Decimal.TryParse(PastHotel.Price.Replace(",", "#").Replace(".", "").Replace("#", "."), out value)) ? Decimal.Parse(PastHotel.Price.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
                        //    var PriceDec = DecimalPriceTreatment(_Hotel.Price);
                        //    var BiggestPriceDec = (Decimal.TryParse(PastHotel.BiggestPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), out value)) ? Decimal.Parse(PastHotel.BiggestPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
                        //    var LowestPriceDec = (Decimal.TryParse(PastHotel.LowestPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), out value)) ? Decimal.Parse(PastHotel.LowestPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
                        //    var NumberSearchesLong = (long)Convert.ToDouble(_Hotel.NumberSearches);
                        //    var SumPriceDec = (Decimal.TryParse(PastHotel.SumPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), out value)) ? Decimal.Parse(PastHotel.SumPrice.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;

                        //    _Hotel.LastPrice = PastHotel.Price;
                        //    _Hotel.DateLastPrice = PastHotel.CurrentExecutionDate;
                        //    _Hotel.PriceDifferencePercentage = ((LastPriceDec / PriceDec - 1) * 100).ToString();
                        //    _Hotel.BiggestPrice = PriceDec > BiggestPriceDec ? _Hotel.Price : PastHotel.BiggestPrice;
                        //    _Hotel.DateBiggestPrice = PriceDec > BiggestPriceDec ? _Hotel.CurrentExecutionDate : PastHotel.DateBiggestPrice;
                        //    _Hotel.LowestPrice = PriceDec < LowestPriceDec ? _Hotel.Price : PastHotel.LowestPrice;
                        //    _Hotel.DateLowestPrice = PriceDec < LowestPriceDec ? _Hotel.CurrentExecutionDate : PastHotel.DateLowestPrice;
                        //    _Hotel.NumberSearches = (NumberSearchesLong + 2);
                        //    _Hotel.SumPrice = (SumPriceDec + PriceDec).ToString();
                        //    _Hotel.AveragePrice = ((SumPriceDec + PriceDec) / (NumberSearchesLong + 1)).ToString();
                        //}
                        //else
                        //{
                        //    _Hotel.LastPrice = _Hotel.Price;
                        //    _Hotel.DateLastPrice = _Hotel.CurrentExecutionDate;
                        //    _Hotel.PriceDifferencePercentage = "0";
                        //    _Hotel.BiggestPrice = _Hotel.Price;
                        //    _Hotel.DateBiggestPrice = _Hotel.CurrentExecutionDate;
                        //    _Hotel.LowestPrice = _Hotel.Price;
                        //    _Hotel.DateLowestPrice = _Hotel.CurrentExecutionDate;
                        //    _Hotel.NumberSearches = 1;
                        //    _Hotel.SumPrice = _Hotel.Price;
                        //    _Hotel.AveragePrice = _Hotel.Price;
                        //}

                        HotelList.Add(_Hotel);
                    }

                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying setting the list of Hotels from ImportFromDecolarWebSite class: {ex.Message}. ", ex);
            }
        }

        private static decimal DecimalPriceTreatment(string value)
        {
            decimal valueOut;
            return (Decimal.TryParse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), out valueOut)) ? Decimal.Parse(value.Replace(",", "#").Replace(".", "").Replace("#", "."), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture) : 0;
        }

        private void SetConfigURL(HotelSearchSettingParameters Search, DateTime? StartDate, DateTime? EndDate)
        {
            CountPage = 25;
            var Url = new URLDecolar();
            currentURL = Url.build(Search, StartDate, EndDate);
            //int cont = 1;
            //while (CountPage < 5 || cont <= 5)
            //{
            //    IWebDriver driver;
            //    WebDriverWait wait;

            //    var options = new ChromeOptions();
            //    options.AddArgument("no-sandbox");
            //    options.AddArguments("headless");
            //    options.AddArguments("window-size=1200x600");

            //    using (driver = new ChromeDriver(AppDomain.CurrentDomain.BaseDirectory, options, TimeSpan.FromMinutes(2000)))
            //    {
            //        var Url = new URLDecolar();
            //        wait = new WebDriverWait(driver, TimeSpan.FromMinutes(2000));
            //        driver.Navigate().GoToUrl(Url.build(Search, StartDate, EndDate));
            //        currentURL = driver.Url;

            //        var HTMLAll = driver.PageSource;

            //        var config = Configuration.Default;
            //        var parser = new HtmlParser();
            //        var document = parser.ParseDocument(HTMLAll);

            //        var ListResults = document.QuerySelectorAll("a[class='pagination-item eva-3-link']");

            //        foreach (var item in ListResults)
            //        {
            //            if (int.TryParse(item.TextContent, out int n))
            //                if (int.Parse(item.TextContent) > CountPage)
            //                    CountPage = int.Parse(item.TextContent);
            //        }
            //        cont++;
            //    }
            //}
        }
    }
}

