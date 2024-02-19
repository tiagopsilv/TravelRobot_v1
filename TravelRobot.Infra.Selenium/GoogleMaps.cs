using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.DevTools;
using OpenQA.Selenium.Support.UI;
using System;
using System.Collections.Generic;
using System.Text;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.Selenium
{
    public class GoogleMaps : IGoogleMaps, ICloneable, IDisposable
    {
        private ChromeDriver driver;
        private WebDriverWait wait;

        public object Clone()
        {
            return this.MemberwiseClone();
        }

        public void Dispose()
        {
        }

        public string GetHtml(string HotelAddress, string ReferencePointA)
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
                    driver.Manage().Timeouts().ImplicitWait = TimeSpan.FromSeconds(200);
                    driver.Manage().Timeouts().PageLoad = TimeSpan.FromSeconds(200);
                    //WebDriverWait wait = new WebDriverWait(driver, TimeSpan.FromMinutes(2000));
                    driver.Navigate().GoToUrl(@"https://www.google.com/maps");

                    driver.FindElement(By.XPath("//button[@id='hArJGc']")).Click();

                    driver.FindElement(By.XPath("//div[@id='sb_ifc51']/input")).Click();
                    driver.FindElement(By.XPath("//div[@id='sb_ifc51']/input")).Clear();
                    driver.FindElement(By.XPath("//div[@id='sb_ifc51']/input")).SendKeys(HotelAddress);

                    //driver.FindElement(By.Id("searchboxinput")).Click();
                    //driver.FindElement(By.Id("searchboxinput")).Clear();
                    //driver.FindElement(By.Id("searchboxinput")).SendKeys(HotelAddress);
                    //driver.FindElement(By.Id("searchboxinput")).SendKeys(Keys.Enter);

                    driver.FindElement(By.XPath("//div[@id='sb_ifc52']/input")).Click();
                    driver.FindElement(By.XPath("//div[@id='sb_ifc52']/input")).Clear();
                    driver.FindElement(By.XPath("//div[@id='sb_ifc52']/input")).SendKeys(ReferencePointA);
                    driver.FindElement(By.XPath("//div[@id='sb_ifc52']/input")).SendKeys(Keys.Enter);

                    if(wait == null)
                        wait = new WebDriverWait(driver, TimeSpan.FromSeconds(20000));

                    wait.Until(driver => driver.FindElement(By.Id("section-directions-trip-details-msg-0")));

                    result = driver.PageSource;
                    driver.Close();
                    driver.Quit();
                    driver.Dispose();
                }

                return result;
            }
            catch (Exception ex)
            {
                //Log.($"The following error occurred when to Selenium try get the URL www.google.com/maps : {ex.Message}. ", ex);
                throw;
            }
        }


    }
}
