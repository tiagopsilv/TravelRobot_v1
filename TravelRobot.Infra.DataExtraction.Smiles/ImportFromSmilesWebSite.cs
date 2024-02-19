
using AngleSharp;
using AngleSharp.Html.Parser;
using Serilog;
using System;
using System.Collections.Generic;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Infra.Selenium;

namespace TravelRobot.Infra.DataExtraction.Smiles
{
    public class ImportFromSmilesWebSite : IImportFromSmilesWebSite
    {
        private List<FrequentFlyer> FrequentFlyerList;

        private IHtmlSearchEnginePage _HtmlSearchEnginePage;

        public ImportFromSmilesWebSite(IHtmlSearchEnginePage HtmlSearchEnginePage)
        {
            _HtmlSearchEnginePage = HtmlSearchEnginePage;
        }

        public List<FrequentFlyer> GetHotelList()
        {
            return FrequentFlyerList;
        }

        public void SetFrequentFlyerList()
        {
            try
            {
  
                FrequentFlyerList = new List<FrequentFlyer>();

                var HTMLAll = _HtmlSearchEnginePage.GetHtml(@"https://www.smiles.com.br/promocao");

                var config = Configuration.Default;
                var parser = new HtmlParser();
                var document = parser.ParseDocument(HTMLAll);

                var ListResults = document.QuerySelectorAll("[id^='promoCardTags']");

                foreach (var item in ListResults)
                {
                    var documentItem = parser.ParseDocument(item.InnerHtml);

                    var _FrequentFlyer = new FrequentFlyer();

                    _FrequentFlyer.CurrentExecutionDate = DateTime.Now;

                    _FrequentFlyer.FrequentFlyerProgramName = "Smiles";

                    _FrequentFlyer.Type = documentItem.GetElementsByClassName("titulo-promo-antes-sorriso")[0].TextContent + " " + documentItem.GetElementsByClassName("titulo-promo-depois-sorriso")[0].TextContent;

                    _FrequentFlyer.Title = documentItem.QuerySelector("div.text-box-promo > h2").TextContent;

                    _FrequentFlyer.Text = documentItem.QuerySelector("div.text-box-promo > p").TextContent;

                    _FrequentFlyer.Validity = documentItem.GetElementsByClassName("card-data-validade")[0].TextContent;

                    _FrequentFlyer.Link = documentItem.GetElementsByClassName("promo-link-footer")[0].GetAttribute("href");

                    FrequentFlyerList.Add(_FrequentFlyer);

                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when trying setting the list of Frequent Flyers from ImportFromSmilesWebSite class: {ex.Message}. ", ex);
            }

        }

    }
 
}
