using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;

namespace TravelRobot.Domain.Interfaces
{
    public interface IReadFileDecolar
    {
        public List<Hotel> ReadLatestData();

    }
}
