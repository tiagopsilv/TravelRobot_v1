using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Enums;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.File
{
    public class SaveFactory : ISaveFactory
    {
   
        private ISaveFromSmilesWebSite _SaveFromSmilesWebSite;
        private ISaveFromHotesWebSite _SaveFromHotesWebSite;
        private ISaveFromHotelHistory _SaveFromHotelHistory;

        public SaveFactory(ISaveFromSmilesWebSite SaveFromSmilesWebSite, ISaveFromHotesWebSite SaveFromHotesWebSite, ISaveFromHotelHistory SaveFromHotelHistory)
        {
            _SaveFromSmilesWebSite = SaveFromSmilesWebSite;
            _SaveFromHotesWebSite = SaveFromHotesWebSite;
            _SaveFromHotelHistory = SaveFromHotelHistory;
        }

        public ISaveFromSmilesWebSite BuildSaveSmilesWebSite()
        {
            return _SaveFromSmilesWebSite;
        }

        public ISaveFromHotesWebSite BuildSaveHotesWebSite()
        {
            return _SaveFromHotesWebSite;
        }

        public ISaveFromHotelHistory BuildSaveHotelHistory()
        {
            return _SaveFromHotelHistory;
        }

    }
}
