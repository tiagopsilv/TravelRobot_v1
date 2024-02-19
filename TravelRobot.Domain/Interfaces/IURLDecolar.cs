using System;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IURLDecolar
    {
        public string build(HotelSearchSettingParameters Search, DateTime? StartDate, DateTime? EndDate);
    }
}
