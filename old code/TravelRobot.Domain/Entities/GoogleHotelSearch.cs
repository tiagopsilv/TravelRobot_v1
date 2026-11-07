using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class GoogleHotelSearch : HotelSearch
    {
        public string HotelName { get; set; }
        public string Rating { get; set; }
        public bool OnlyTop { get; set; }   
    }
}
