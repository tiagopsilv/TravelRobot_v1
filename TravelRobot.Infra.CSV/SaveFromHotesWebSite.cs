using Serilog;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.File
{
    public class SaveFromHotesWebSite : ISaveFromHotesWebSite
    {
        private List<Hotel> _HotelsList = new List<Hotel>();
        private const string _DirectoryHotelList = @"D:\Projetos\Viagem\Hoteis_Por_Dia\";
        private const string _DirectoryHTMLList = @"D:\Projetos\Viagem\Hoteis_Por_Dia\Htmls\";

        private string HotelNameErro = "";
        private string CityNameErro = "";
        private string WebSiteErro = "";

        public int Count => throw new NotImplementedException();

        public bool IsReadOnly => throw new NotImplementedException();

        public List<Hotel> this[int index] { get => throw new NotImplementedException(); set => throw new NotImplementedException(); }

        public SaveFromHotesWebSite()
        {
            _HotelsList = new List<Hotel>();
        }

        public void Save()
        {
            bool isEmpty = (_HotelsList.Count == 0 ? true : false);
            if (!isEmpty)
            {
                WriteHotelList();
                WriteHtmlslList();
            }
        }

        private void WriteHotelList()
        {
            try
            {
                var CityNameList = _HotelsList.GroupBy(x => new { x.CityName }).Select(v => v.Key.CityName).ToList();

                foreach (string CityNameItem in CityNameList)
                {
                    var HotelsListItem = _HotelsList.Where(t => t.CityName == CityNameItem).ToList();

                    var path = _DirectoryHotelList + "HotelsList_" + HotelsListItem[0].CityName + "_" + HotelsListItem[0].CurrentExecutionDate.ToString("yyyyMMdd") + ".csv";

                    using (var writer = new StreamWriter(path))
                    {

                        foreach (Hotel item in HotelsListItem)
                        {
                            var text = "";

                            HotelNameErro = item.HotelName;
                            CityNameErro = item.CityName;
                            WebSiteErro = item.WebSite;

                            text += item.CurrentExecutionDate.ToString("yyyy-MM-dd");
                            text += ";";
                            text += item.WebSite;
                            text += ";";
                            text += ((item.SearchStartDate.HasValue) ? item.SearchStartDate.Value.ToString("yyyy-MM-dd") : "");
                            text += ";";
                            text += ((item.SearchEndDate.HasValue) ? item.SearchEndDate.Value.ToString("yyyy-MM-dd") : "");
                            text += ";";
                            text += item.CityName;
                            text += ";";
                            text += item.HotelName;
                            text += ";";
                            text += String.Format("{0:0,##}", item.Price);
                            text += ";";
                            text += item.Rating;
                            text += ";";
                            text += item.PaymentConditions;
                            text += ";";
                            text += item.Nights;
                            text += ";";
                            text += item.People;
                            text += ";";
                            text += item.HotelAddress;
                            text += ";";
                            text += item.DistanceBetweenKM;
                            text += ";";
                            text += item.GuestReviews_Rating;
                            text += ";";
                            text += item.GuestReviews_Amenities;
                            text += ";";
                            text += item.GuestReviews_Cleaning;
                            text += ";";
                            text += item.GuestReviews_Comfort;
                            text += ";";
                            text += item.GuestReviews_CostBenefit;
                            text += ";";
                            text += item.GuestReviews_Employees;
                            text += ";";
                            text += item.GuestReviews_Location;
                            text += ";";
                            text += item.GuestReviews_NumberOfReviews;
                            text += ";";
                            //text += item.LastPrice;
                            //text += ";";
                            //text += ((item.DateLastPrice.HasValue) ? item.DateLastPrice.Value.ToString("yyyy-MM-dd") : "");
                            //text += ";";
                            //text += item.PriceDifferencePercentage;
                            //text += ";";
                            //text += item.BiggestPrice;
                            //text += ";";
                            //text += ((item.DateBiggestPrice.HasValue) ? item.DateBiggestPrice.Value.ToString("yyyy-MM-dd") : "");**
                            //text += ";";
                            //text += item.LowestPrice;
                            //text += ";";
                            //text += ((item.DateLowestPrice.HasValue) ? item.DateLowestPrice.Value.ToString("yyyy-MM-dd") : "");
                            //text += ";";
                            //text += item.NumberSearches;
                            //text += ";";
                            //text += item.SumPrice;
                            //text += ";";
                            //text += item.AveragePrice;
                            text += ";";
                            text += ((item.Link != null) ? item.Link.Replace(";", "#$replaceWebSiteHotes#$") : "");

                            text = Regex.Replace(TrimSpacesBetweenString(text), @"\r\n?|\n", "");

                            writer.WriteLine(text);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to writing the Hotels's csv file, HotelName {HotelNameErro} - CityName {CityNameErro} - WebSite {WebSiteErro} : {ex.Message}. ", ex);
            }
        }

        private string TrimSpacesBetweenString(string text)
        {
            var mystring = text.Split(new string[] { " " }, StringSplitOptions.None);
            string result = string.Empty;
            foreach (var mstr in mystring)
            {
                var ss = mstr.Trim();
                if (!string.IsNullOrEmpty(ss))
                {
                    result = result + ss + " ";
                }
            }
            return result.Trim();

        }

        private void WriteHtmlslList()
        {
            try
            {
                var path = _DirectoryHTMLList + "HtmlHotel_" + _HotelsList[0].CityName + "_" + _HotelsList[0].CurrentExecutionDate.ToString("yyyyMMdd") + ".html";

                using (FileStream fs = new FileStream(path, FileMode.Create))
                {
                    using (var writer = new StreamWriter(fs, Encoding.UTF8))
                    {

                        writer.WriteLine("<H1> DATE: " + _HotelsList[0].CurrentExecutionDate.ToString("yyyyMMdd") + "</H1>");

                        foreach (Hotel item in _HotelsList)
                        {

                            HotelNameErro = item.HotelName;
                            CityNameErro = item.CityName;
                            WebSiteErro = item.WebSite;

                            writer.WriteLine(item.Html);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to writing the Hotels HTML's csv file, HotelName {HotelNameErro} - CityName {CityNameErro} - WebSite {WebSiteErro} : {ex.Message}. ", ex);
                throw;
            }
        }

        public void SetList(List<Hotel> ItemList)
        {
            _HotelsList = ItemList;
        }

        public int IndexOf(List<Hotel> item)
        {
            throw new NotImplementedException();
        }

        public void Insert(int index, List<Hotel> item)
        {
            throw new NotImplementedException();
        }

        public void RemoveAt(int index)
        {
            throw new NotImplementedException();
        }

        public void Add(List<Hotel> item)
        {
            throw new NotImplementedException();
        }

        public void Clear()
        {
            throw new NotImplementedException();
        }

        public bool Contains(List<Hotel> item)
        {
            throw new NotImplementedException();
        }

        public void CopyTo(List<Hotel>[] array, int arrayIndex)
        {
            throw new NotImplementedException();
        }

        public bool Remove(List<Hotel> item)
        {
            throw new NotImplementedException();
        }

        public IEnumerator<List<Hotel>> GetEnumerator()
        {
            throw new NotImplementedException();
        }

        IEnumerator IEnumerable.GetEnumerator()
        {
            throw new NotImplementedException();
        }
    }
}
