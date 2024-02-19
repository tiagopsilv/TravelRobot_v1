using System;
using System.Collections.Generic;
using System.Text;

namespace TravelRobot.Domain.Entities
{
    public class FrequentFlyer
    {
        public DateTime CurrentExecutionDate { get; set; }
        public string FrequentFlyerProgramName { get; set; }
        public string Type { get; set; }
        public string Title { get; set; }
        public string Text { get; set; }
        public string Number { get; set; }
        public string Validity { get; set; }
        public string Link { get; set; }
    }
}
