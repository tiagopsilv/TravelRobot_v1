using System;
using System.Collections.Generic;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IGoogleHotels : ICloneable, IDisposable
    {
        public List<string> GetHotels(string City, DateTime StartDate, DateTime EndDate);
        public List<SeleniumReturns> GetHotelsPrices(string Url);
        public string GetGeneralInformation(string Url);
    }
}