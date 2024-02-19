using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class HotelSearchSettingParameters
    {
        public string CityName { get; set; }
        public string CityCode { get; set; }
        public string TextForSearch { get; set; }
        public string ReferencePointA { get; set; }
        public DateTime? Start { get; set; }
        public DateTime? End { get; set; }
        public string WebSiteURL { get; set; }
    }
}
