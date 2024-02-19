using System;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.DataExtraction.Decolar
{
    public class URLDecolar : IURLDecolar
    {
        //https://www.decolar.com/accommodations/results/CIT_5227/2022-06-07/2022-06-08/

        private string URLDetails_1 { get; set; }

        private void setURLDetails()
        {
            URLDetails_1 = "/accommodations/results/";
        }

        public string build(HotelSearchSettingParameters Search, DateTime? StartDate, DateTime? EndDate)
        {
            setURLDetails();
            return Search.WebSiteURL + URLDetails_1 + Search.CityCode + "/" + StartDate.Value.ToString("yyyy-MM-dd") + "/" + EndDate.Value.ToString("yyyy-MM-dd") + "/";
        }
    }
}
