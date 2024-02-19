using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Layout;

namespace TravelRobot.Domain.Interfaces
{
    public interface IParameter
    {
        public SearchReviewsBookingLayout GetSearchReviewsBookingLayout();
        public SearchImportFromGoogleMapsLayout GetSearchImportFromGoogleMapsLayout();
    }
}
