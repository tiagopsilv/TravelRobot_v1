using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IImportFromSmilesWebSite
    {
        public List<FrequentFlyer> GetHotelList();
        public void SetFrequentFlyerList();
    }
}
