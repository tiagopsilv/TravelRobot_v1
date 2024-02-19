using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IImportFromDecolarWebSite
    {
        public List<Hotel> GetHotelList();
        public void SetHotelList(HotelSearchSettingParameters HotelSearchSettingRules);
    }
}
