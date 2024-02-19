using Microsoft.Extensions.DependencyInjection;
using TravelRobot.Application;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Infra.DataExtraction.Booking;
using TravelRobot.Infra.DataExtraction.Decolar;
using TravelRobot.Infra.DataExtraction.Google;
using TravelRobot.Infra.DataExtraction.Smiles;
using TravelRobot.Infra.Email;
using TravelRobot.Infra.File;
using TravelRobot.Infra.Parameter;
using TravelRobot.Infra.ReadData;
using TravelRobot.Infra.ReadData.Decolar;
using TravelRobot.Infra.Selenium;

namespace TravelRobot.CrossCutting
{
    public class Dependency
    {
        public static ServiceCollection RegisterDependency()
        {
            var services = new ServiceCollection();

            services.AddTransient<IImportFromDecolarWebSite, ImportFromDecolarWebSite>();
            services.AddTransient<IURLDecolar, URLDecolar>();
            services.AddTransient<IImportFromSmilesWebSite, ImportFromSmilesWebSite>();
            services.AddTransient<ISendEmail, SendEmail>();
            services.AddTransient<ISaveFromHotesWebSite, SaveFromHotesWebSite>();
            services.AddTransient<IReadFileDecolar, ReadFileDecolar>();
            services.AddTransient<IHtmlSearchEnginePage, HtmlSearchEnginePage>();
            services.AddTransient<IDesignerHotelHistory, DesignerHotelHistory>();
            services.AddTransient<ISaveFromHotelHistory, SaveFromHotelHistory>();
            services.AddTransient<IReadFileHotelHistory, ReadFileHotelHistory>();
            services.AddTransient<IGoogleHotels, GoogleHotels>();
            services.AddTransient<IStart, Start>();
            services.AddTransient<IImportFromGoogleWebSite, ImportFromGoogleWebSite>();
            services.AddTransient<ISearchDateCityRules, SearchDateCityRules>();
            services.AddTransient<ISearchReviewsBooking, SearchReviewsBooking>();
            services.AddTransient<IBookingReviews, BookingReviews>();
            services.AddTransient<IGoogleMaps, GoogleMaps>();
            services.AddTransient<IImportFromGoogleMaps, ImportFromGoogleMaps>();
            services.AddTransient<IParameter, Parameter>();
            services.AddTransient<ISaveFromSmilesWebSite, SaveFromSmilesWebSite>();
            services.AddTransient<ISaveFactory, SaveFactory>();

            return services;    
        }
    }
}
