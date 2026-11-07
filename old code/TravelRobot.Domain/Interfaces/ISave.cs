using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Interfaces
{
    public interface ISave<T1> : IList<T1>
    {
        public void SetList(T1 ItemList);
        public void Save();
    }
}
