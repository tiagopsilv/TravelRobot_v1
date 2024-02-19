using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Interfaces
{
    public interface IBookingReviews : IDisposable
    {
        public string GetHtml(string HotelSearch);
        public object Clone();
    }
}
