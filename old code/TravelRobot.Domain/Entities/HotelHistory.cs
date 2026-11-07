using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class HotelHistory
    {
        public DateTime CurrentExecutionDate { get; set; }
        public string CityName { get; set; }
        public string HotelName { get; set; }
        public string Rating { get; set; }
        public string LastPrice { get; set; }
        public DateTime? DateLastPrice { get; set; }
        public string PriceDifferencePercentage { get; set; }
        public string BiggestPrice { get; set; }
        public DateTime? DateBiggestPrice { get; set; }
        public string LowestPrice { get; set; }
        public DateTime? DateLowestPrice { get; set; }
        public long NumberSearches { get; set; }
        public string SumPrice { get; set; }
        public string AveragePrice { get; set; }

    }
}
