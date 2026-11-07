using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Interfaces
{
    public interface IHtmlSearchEnginePage
    {
        public string GetHtml(string Url);
    }
}
