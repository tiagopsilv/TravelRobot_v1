using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using System;
using Serilog;
using OpenQA.Selenium;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.Selenium
{
    public class BookingReviews : IBookingReviews, ICloneable, IDisposable
    {
        private ChromeDriver driver;

        public object Clone()
        {
            return this.MemberwiseClone();
        }

        public void Dispose()
        {
        }

        public string GetHtml(string HotelSearch)
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
                    //WebDriverWait wait = new WebDriverWait(driver, TimeSpan.FromMinutes(2000));
                    driver.Navigate().GoToUrl(@"https://www.google.com/");

                    driver.FindElement(By.Name("q")).Clear();
                    driver.FindElement(By.Name("q")).SendKeys(HotelSearch);

                    IWebElement element = driver.FindElement(By.XPath("//input[@name='btnI']"));

                    IJavaScriptExecutor executor = (IJavaScriptExecutor)driver;
                    executor.ExecuteScript("arguments[0].click();", element);

                    result = driver.PageSource;
                    driver.Close();
                    driver.Quit();
                    driver.Dispose();
                }

                return result;
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to Selenium try get the URL www.google.com : {ex.Message}. ", ex);
                throw;
            }
        }

    }
}
