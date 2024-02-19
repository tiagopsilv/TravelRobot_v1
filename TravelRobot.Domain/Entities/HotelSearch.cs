using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class HotelSearch
    {
        public bool Enable { get; set; }
        public string CityName { get; set; }
        public string CityCode { get; set; }
        public string TextForSearch { get; set; }
        public string ReferencePointA { get; set; }
        public string StartDate { get; set; }
        public string EndDate { get; set; }
        public string RangeSearchType { get; set; }
        public string WebSiteURL { get; set; }
    }
}
