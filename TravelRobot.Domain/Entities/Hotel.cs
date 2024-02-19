using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class Hotel
    {
        public DateTime CurrentExecutionDate { get; set; }
        public DateTime? SearchStartDate { get; set; }
        public DateTime? SearchEndDate { get; set; }
        public string CityName { get; set; }
        public string HotelName { get; set; }
        public string Link { get; set; }
        public string Price { get; set; }
        public string Rating { get; set; }
        public string PaymentConditions { get; set; }
        public string Nights { get; set; }
        public string People { get; set; }
        public string Html { get; set; }
        public string WebSite { get; set; }
        public string HotelAddress { get; set; }
        public string DistanceBetweenKM { get; set; }
        public string GuestReviews_Rating { get; set; }
        public string GuestReviews_Employees { get; set; }
        public string GuestReviews_Comfort { get; set; }
        public string GuestReviews_Amenities { get; set; }
        public string GuestReviews_Cleaning { get; set; }
        public string GuestReviews_CostBenefit { get; set; }
        public string GuestReviews_Location { get; set; }
        public string GuestReviews_WiFi { get; set; }
        public string GuestReviews_NumberOfReviews { get; set; }

        //public string LastPrice { get; set; }
        //public DateTime? DateLastPrice { get; set; }
        //public string PriceDifferencePercentage { get; set; }
        //public string BiggestPrice { get; set; }
        //public DateTime? DateBiggestPrice { get; set; }
        //public string LowestPrice { get; set; }
        //public DateTime? DateLowestPrice { get; set; }
        //public long NumberSearches { get; set; }
        //public string SumPrice { get; set; }
        //public string AveragePrice { get; set; }
    }
}
