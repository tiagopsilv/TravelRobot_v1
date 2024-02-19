using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using Serilog;
using System;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.Selenium
{
    public class HtmlSearchEnginePage : IHtmlSearchEnginePage
    {
        private ChromeDriver driver;
        private WebDriverWait wait;

        public string GetHtml(string Url)
        {
            try
            {
                var result = "";
                var options = new ChromeOptions();
                options.AddArgument("no-sandbox");
                options.AddArguments("headless");
                options.AddArguments("window-size=1200x600");

                using (driver = new ChromeDriver(AppDomain.CurrentDomain.BaseDirectory, options, TimeSpan.FromMinutes(2000)))
                {
                    wait = new WebDriverWait(driver, TimeSpan.FromMinutes(2000));
                    driver.Navigate().GoToUrl(Url);

                    result = driver.PageSource;
                }

                return result;
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to Selenium try get the URL {Url} : {ex.Message}. ", ex);
                throw;
            }
        }
    }
}
