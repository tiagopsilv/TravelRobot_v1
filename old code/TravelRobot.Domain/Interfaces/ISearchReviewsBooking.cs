using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface ISearchReviewsBooking
    {
        public void SetHotel(Hotel InfHotel);
        public void SetHotel(List<Hotel> InfHotel);
        public void BuildHTMLPage();
        public List<GuestReviews> GetGuestReviewslList();
    }
}
