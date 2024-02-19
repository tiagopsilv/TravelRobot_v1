using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Support.UI;
using Serilog;
using System;
using System.Collections.Generic;
using System.Threading;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.Selenium
{
    public class GoogleHotels : IGoogleHotels, ICloneable, IDisposable
    {
        private ChromeDriver driver;
        private WebDriverWait wait;
        public List<string> GetHotels(string City, DateTime StartDate, DateTime EndDate)
        {
            var result = new List<string>();

            try
            {
                var options = new ChromeOptions();
                options.AddArgument("no-sandbox");
                options.AddArguments("headless");
                options.AddArguments("window-size=1200x600");

                using (driver = new ChromeDriver(AppDomain.CurrentDomain.BaseDirectory, options, TimeSpan.FromMinutes(2000)))
                {
                    driver.Navigate().GoToUrl("https://www.google.com.br/travel/hotels/" + City);

                    driver.FindElement(By.XPath("//input[@aria-label='Fazer check-in']")).Clear();
                    driver.FindElement(By.XPath("//input[@aria-label='Fazer check-in']")).SendKeys(StartDate.ToString("dd/MM/yyyy"));

                    driver.FindElement(By.XPath("//input[@aria-label='Fazer check-out']")).Clear();
                    driver.FindElement(By.XPath("//input[@aria-label='Fazer check-out']")).SendKeys(EndDate.ToString("dd/MM/yyyy"));
                    driver.FindElement(By.XPath("//input[@aria-label='Fazer check-out']")).SendKeys(Keys.Enter);

                    ScrollToBottom(driver);

                    if (driver.PageSource.Length > 0)
                        result.Add(driver.PageSource);

                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to Selenium try get the URL https://www.google.com.br/travel/hotels/Roma : {ex.Message}. ", ex);
            }

            return result;
        }

        public List<SeleniumReturns> GetHotelsPrices(string Url)
        {
            List<SeleniumReturns> result = new List<SeleniumReturns>();
            try
            { 
                var options = new ChromeOptions();
                options.AddArgument("no-sandbox");
                options.AddArguments("headless");
                options.AddArguments("window-size=1200x600");

                using (driver = new ChromeDriver(AppDomain.CurrentDomain.BaseDirectory, options, TimeSpan.FromMinutes(2000)))
                {
                    driver.Navigate().GoToUrl(Url);

                    result.Add(new SeleniumReturns { Tag = "GeneralInformation", Return = driver.PageSource });

                    var elements = driver.FindElement(By.XPath("//div[@id='prices']"));

                    if (FindElementIfExists(driver, "//div[@id='prices']"))
                    {

                        driver.FindElement(By.XPath("//div[@id='prices']")).Click();

                        if (FindElementIfExists(driver, "//span[@class='DPvwYc AWqXob']"))
                        {
                            driver.FindElement(By.XPath("//span[@class='DPvwYc AWqXob']")).Click();
                        }

                        result.Add(new SeleniumReturns { Tag = "HotelsPrices", Return = driver.PageSource });

                    }
                    driver.Close();
                    driver.Quit();
                    driver.Dispose();

                }

            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to Selenium try get the URL {Url}: {ex.Message}. ", ex);
            }
            return result;
        }

        public string GetGeneralInformation(string Url)
        {
            string result = "";
            try
            {
                var options = new ChromeOptions();
                options.AddArgument("no-sandbox");
                options.AddArguments("headless");
                options.AddArguments("window-size=1200x600");

                using (driver = new ChromeDriver(AppDomain.CurrentDomain.BaseDirectory, options, TimeSpan.FromMinutes(2000)))
                {
                    driver.Navigate().GoToUrl(Url);
                    result = driver.PageSource;
                }

            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to Selenium try get the URL {Url}: {ex.Message}. ", ex);
            }
            return result;
        }

        private void ScrollToBottom(IWebDriver driver)
        {
            long scrollHeight = 0;
            do
            {
                IJavaScriptExecutor js = (IJavaScriptExecutor)driver;
                var newScrollHeight = (long)js.ExecuteScript("return document.body.scrollHeight;");

                Thread.Sleep(2000);

                for (long i = (newScrollHeight> 4239 ? (newScrollHeight - 100) : (newScrollHeight/2)); i < newScrollHeight; i = i+3)
                    newScrollHeight = (long)js.ExecuteScript("window.scrollTo(0, " + i + "); return document.body.scrollHeight;");

                newScrollHeight = (long)js.ExecuteScript("window.scrollTo(0, document.body.scrollHeight); return document.body.scrollHeight;");

                if (newScrollHeight == scrollHeight)
                {
                    break;
                }
                else
                {
                    scrollHeight = newScrollHeight;
                    Thread.Sleep(4000);
                 }
            } while (true);
        }

        public IWebElement SearchForElement(IWebDriver driver, string ClickElementXPath)
        {
            bool staleElement = true;
            IWebElement result = null;

            while(staleElement)
            {
                try
                {
                    WebDriverWait wait = new WebDriverWait(driver, TimeSpan.FromMinutes(1));
                    IWebElement el = wait.Until(e => e.FindElement(By.XPath(ClickElementXPath)));
                    result = el;
                    staleElement = false;
                }
                catch(StaleElementReferenceException e)
                {
                    staleElement = true;
                }
            }
            return result;
        }

        private bool IsElementPresent(IWebDriver driver, string ClickElementXPath)
        {
            var Result = false;
            var Count = 1;
            while (Count < 100 && !Result)
            {
                try
                {
                    Thread.Sleep(20);
                    driver.FindElement(By.XPath(ClickElementXPath));
                    Result = true;
                }
                catch (NoSuchElementException)
                {
                    Result = false;
                }
                Count++;
                if (Count == 5) Thread.Sleep(100);
            }
            return Result;
        }

        private bool FindElementIfExists(IWebDriver driver, string by)
        {
            List<IWebElement> e = new List<IWebElement>();
            e.AddRange(driver.FindElements(By.XPath(by)));
            return (e.Count >= 1) ? true : false;
        }

        public object Clone()
        {
            return this.MemberwiseClone();
        }

        public void Dispose()
        {
        }
    }
}