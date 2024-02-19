using Serilog;
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;

namespace TravelRobot.Infra.File
{
    public class SaveFromSmilesWebSite : ISaveFromSmilesWebSite
    {
        private List<FrequentFlyer> _FrequentFlyersList = new List<FrequentFlyer>();
        private const string _DirectoryHotelList = @"D:\Projetos\Viagem\ProgramasFi\";

        private string FrequentFlyerProgramNameError = "";
        private string TitleError = "";

        public int Count => throw new NotImplementedException();

        public bool IsReadOnly => throw new NotImplementedException();

        public List<FrequentFlyer> this[int index] { get => throw new NotImplementedException(); set => throw new NotImplementedException(); }

        public SaveFromSmilesWebSite()
        {
            _FrequentFlyersList = new List<FrequentFlyer>();
        }

        public void SetFrequentFlyerList(List<FrequentFlyer> FrequentFlyersList)
        {
            _FrequentFlyersList = FrequentFlyersList;
        }


        public void SetList(List<FrequentFlyer> ItemList)
        {
            _FrequentFlyersList = ItemList;
        }

        public void Save()
        {
            try
            {
                var path = _DirectoryHotelList + "FrequentFlyersList_" + _FrequentFlyersList[0].FrequentFlyerProgramName + "_" + _FrequentFlyersList[0].CurrentExecutionDate.ToString("yyyyMMdd") + ".csv";

                using (var writer = new StreamWriter(path))
                {

                    foreach (FrequentFlyer item in _FrequentFlyersList)
                    {
                        var text = "";

                        FrequentFlyerProgramNameError = item.FrequentFlyerProgramName;
                        TitleError = item.Title;

                        text += item.CurrentExecutionDate.ToString("yyyy-MM-dd") + ";";
                        text += item.FrequentFlyerProgramName + ";";
                        text += item.Type + ";";
                        text += item.Title + ";";
                        text += Regex.Replace(item.Text, @"\t|\n|\r", "") + ";";
                        text += item.Number + ";";
                        text += item.Validity + ";";
                        text += item.Link + ";";

                        writer.WriteLine(text);
                    }
                }
            }
            catch (Exception ex)
            {
                Log.Error($"The following error occurred when to writing the Frequent Flyers's csv file, Frequent Flyer Program Name {FrequentFlyerProgramNameError} - Title {TitleError} : {ex.Message}. ", ex);
            }
        }

        public int IndexOf(List<FrequentFlyer> item)
        {
            throw new NotImplementedException();
        }

        public void Insert(int index, List<FrequentFlyer> item)
        {
            throw new NotImplementedException();
        }

        public void RemoveAt(int index)
        {
            throw new NotImplementedException();
        }

        public void Add(List<FrequentFlyer> item)
        {
            throw new NotImplementedException();
        }

        public void Clear()
        {
            throw new NotImplementedException();
        }

        public bool Contains(List<FrequentFlyer> item)
        {
            throw new NotImplementedException();
        }

        public void CopyTo(List<FrequentFlyer>[] array, int arrayIndex)
        {
            throw new NotImplementedException();
        }

        public bool Remove(List<FrequentFlyer> item)
        {
            throw new NotImplementedException();
        }

        public IEnumerator<List<FrequentFlyer>> GetEnumerator()
        {
            throw new NotImplementedException();
        }

        IEnumerator IEnumerable.GetEnumerator()
        {
            throw new NotImplementedException();
        }
    }
}
