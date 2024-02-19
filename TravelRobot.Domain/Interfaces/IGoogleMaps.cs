using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Interfaces
{
    public interface IGoogleMaps: ICloneable, IDisposable
    {
        public string GetHtml(string HotelAddress, string ReferencePointA);
    }
}
