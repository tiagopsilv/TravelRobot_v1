using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface ISaveFactory
    {
        public ISaveFromSmilesWebSite BuildSaveSmilesWebSite();
        public ISaveFromHotesWebSite BuildSaveHotesWebSite();
        public ISaveFromHotelHistory BuildSaveHotelHistory();
    }
}
