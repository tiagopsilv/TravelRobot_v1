using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Application
{
    public class SearchDateCityRules : ISearchDateCityRules
    {

        public List<HotelSearchSettingParameters> GetListSearch()
        {
            var DatesList = new List<HotelSearchSettingParameters>();

            foreach (var Search in GetHotelSearch())
            {
                if (Search.Enable)
                {
                    var _StartDate = GetStartDate(Search);
                    var _EndDate = GetEndDate(Search);


                    foreach (var DateListSearch in BuildListSearch(Search, _StartDate, _EndDate))
                        DatesList.Add(new HotelSearchSettingParameters { CityCode = Search.CityCode, CityName = Search.CityName, TextForSearch = Search.TextForSearch, ReferencePointA = Search.ReferencePointA, Start = DateListSearch.Start, End = DateListSearch.End, WebSiteURL = Search.WebSiteURL });
                }

            }

            return DatesList;

        }

        private List<DatesRange> BuildListSearch(HotelSearch Search, DateTime? StartDate, DateTime? EndDate)
        {
            var DateListSearch = new List<DatesRange>();
            var RangeSearchType = Search.RangeSearchType;
            var Date = StartDate;

            if (RangeSearchType == "Week")
            {
                while (Date < EndDate)
                {
                    DateTime? DataStartWeek = Date;
                    DateTime? nextSunday = Date.Value.AddDays((((int)DayOfWeek.Sunday - (int)Date.Value.DayOfWeek + 7) % 7));
                    DateListSearch.Add(new DatesRange { Start = DataStartWeek, End = nextSunday });
                    Date = nextSunday.Value.AddDays(1);
                }
            }
            else if (RangeSearchType == "JustOneDay")
            {
                DateListSearch.Add(new DatesRange { Start = StartDate, End = EndDate });
            }
            return DateListSearch;
        }

        private static DateTime? GetStartDate(HotelSearch Search)
        {
            DateTime? StartDate = null;
            switch (Search.StartDate)
            {
                case "CurrentDate":
                    StartDate = DateTime.Now;
                    break;
                default:
                    break;
            }

            if (StartDate == null && IsDateTime(Search.StartDate))
            {
                StartDate = DateTime.ParseExact(Search.StartDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            }

            return StartDate;
        }

        private static DateTime? GetEndDate(HotelSearch Search)
        {
            DateTime? GetEndDate = null;
            DateTime setDate = IsDateTime(Search.StartDate) ? DateTime.ParseExact(Search.StartDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture) : DateTime.Now;

            switch (Search.EndDate)
            {
                case "EndOfYear":
                    GetEndDate = new DateTime(setDate.Year, 12, 31);
                    break;
                case "EndOfMonth":
                    GetEndDate = new DateTime(setDate.Year, setDate.Month, DateTime.DaysInMonth(setDate.Year, setDate.Month));
                    break;
                default:
                    break;
            }

            if (GetEndDate == null && IsDateTime(Search.EndDate))
            {
                GetEndDate = DateTime.ParseExact(Search.EndDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
            }

            return GetEndDate;
        }

        private List<HotelSearch> GetHotelSearch()
        {
            string filePath = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, @"..\..\..\")) + @"ConfigHotelSearch.json";
            string _countryJson = File.ReadAllText(filePath);
            return JsonConvert.DeserializeObject<List<HotelSearch>>(_countryJson);
        }

        private static bool IsDateTime(string txtDate)
        {
            DateTime tempDate;
            return DateTime.TryParse(txtDate, out tempDate);
        }
    }
}
