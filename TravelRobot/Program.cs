using Microsoft.Extensions.DependencyInjection;
using Serilog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using TravelRobot.CrossCutting;
using TravelRobot.Domain.Entities;
using TravelRobot.Domain.Interfaces;
using TravelRobot.Infra.DataExtraction.Decolar;
using TravelRobot.Infra.DataExtraction.Smiles;
using TravelRobot.Infra.File;
using TravelRobot.Infra.ReadData.Decolar;

namespace TravelRobot
{
    internal class Program
    {
        static void Main(string[] args)
        {
            Log.Logger = new LoggerConfiguration().MinimumLevel.Debug().WriteTo.Console().WriteTo.File("C:\\LOGS_ROBOTS\\TravelRobot\\log.txt", rollingInterval: RollingInterval.Day).CreateLogger();
            var serviceProvider = Dependency.RegisterDependency().BuildServiceProvider();
            serviceProvider.GetService<IStart>().Main();
        }

    }
}
