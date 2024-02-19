using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IImportFromGoogleMaps
    {
        public void SetHotel(List<Hotel> InfHotel);
        public void BuildHTMLPage(List<HotelSearchSettingParameters> ReferencePointA);
        public List<DistanceBetween> GetListDistanceBetween();
    }
}
