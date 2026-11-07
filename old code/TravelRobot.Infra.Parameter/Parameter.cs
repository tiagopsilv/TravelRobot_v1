using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.IO;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Domain.Layout;

namespace TravelRobot.Infra.Parameter
{
    public class Parameter : IParameter
    {
        public SearchReviewsBookingLayout GetSearchReviewsBookingLayout()
        {
            string filePath = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, @"..\..\..\")) + @"\Layout\SearchReviewsBookingLayout.json";
            string _countryJson = File.ReadAllText(filePath);
            return JsonConvert.DeserializeObject<SearchReviewsBookingLayout>(_countryJson);
        }

        public SearchImportFromGoogleMapsLayout GetSearchImportFromGoogleMapsLayout()
        {
            string filePath = Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, @"..\..\..\")) + @"\Layout\SearchImportFromGoogleMapsLayout.json";
            string _countryJson = File.ReadAllText(filePath);
            return JsonConvert.DeserializeObject<SearchImportFromGoogleMapsLayout>(_countryJson);
        }
    }
}
