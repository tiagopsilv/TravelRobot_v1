using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface ISaveFromHotelHistory
    {
        public void SetHotelList(List<HotelHistory> HotelHistoryList);
        public void Salve();
    }
}
