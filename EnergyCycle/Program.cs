using CryptoCompare;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using TradeTend.Extension;
using TradeTend.Orientation;

namespace TradeTend
{


    class Program
    {

        static double GetStandardDeviation(List<double> doubleList)
        {
            double average = doubleList.Average();
            double sumOfDerivation = 0;
            foreach (double value in doubleList)
            {
                sumOfDerivation += (value) * (value);
            }
            double sumOfDerivationAverage = sumOfDerivation / (doubleList.Count - 1);
            return Math.Sqrt(sumOfDerivationAverage - (average * average));
        }


        static double[] MovingAverage(int period, double[] source)
        {
            var ma = new double[source.Length];

            double sum = 0;
            for (int bar = 0; bar < period; bar++)
                sum += source[bar];

            ma[period - 1] = sum / period;

            for (int bar = period; bar < source.Length; bar++)
                ma[bar] = ma[bar - 1] + source[bar] / period
                                      - source[bar - period] / period;

            return ma;
        }



        // Below Our current value minus -1
        bool l1bl2 = false;
        bool l2bl1 = false;
        bool l3bl1 = false;
        bool l3bl2 = false;


        // Higher our current value minus -1
        bool l1hl2 = false;
        bool l2hl1 = false;
        bool l3hl1 = false;
        bool l3hl2 = false;


        // Pivot between lower/higher value 
        bool pivotal = false;


        static bool CompareList(int x, int y)
        {
            return x > y;
        }

        static KeyValuePair<int, bool> CompareL1L2L3Value(int l1 = 1, int l2 = 2, int l3 = 3, bool highvalue = true)
        {
            bool returnonfirstmatch = false;
            var matchedvalue1 = (l1 > l2 && highvalue || l1 < l2 && !highvalue) == true;
            var matchedvalue2 = (l2 > l3 && highvalue || l2 < l3 && !highvalue) == true;
            var matchedvalue3 = (l3 > l1 && highvalue || l3 < l1 && !highvalue) == true;

            var multimatch12 = matchedvalue1 && matchedvalue2;
            var multimatch13 = matchedvalue1 && matchedvalue3;
            var multimatch32 = matchedvalue2 && matchedvalue3;
          

            if (!highvalue)
            {
                matchedvalue1 = (l1 < l2 && highvalue || l1 < l3) == true;
                matchedvalue2 = (l2 < l3 && highvalue || l2 < l1) == true;
                matchedvalue3 = (l3 < l1 && highvalue || l3 < l2) == true;


                 multimatch12 = matchedvalue1 && matchedvalue2;
                 multimatch13 = matchedvalue1 && matchedvalue3;
                 multimatch32 = matchedvalue2 && matchedvalue3;

                if (multimatch12)
                {
                    if (l1 > l3)
                    {
                        return new KeyValuePair<int, bool>(3, true);

                    }
                    else
                    {
                        return new KeyValuePair<int, bool>(2, true);

                    }
                }

                if (multimatch32)
                {
                    if (l2 > l3)
                    {
                        return new KeyValuePair<int, bool>(3, true); 

                    }
                    else
                    {
                        return new KeyValuePair<int, bool>(2, true);

                    }
                }
            }
            if (matchedvalue2 && matchedvalue3)
            {
                if (l2 < l3)
                {
                    if (matchedvalue2) { return new KeyValuePair<int, bool>(2, true); }

                }
                else
                {
                    if (matchedvalue3) { return new KeyValuePair<int, bool>(3, true); }

                }
            }

            if (matchedvalue1) { return new KeyValuePair<int, bool>(1, true); }
            if (matchedvalue2) { return new KeyValuePair<int, bool>(2, true); }
            if (matchedvalue3) { return new KeyValuePair<int, bool>(3, true); }

            return new KeyValuePair<int, bool>(0, false);
        }

        static int GetOurTrendBitchWithIndex()
        {



            int[] L1 = { 46, 49, 35 };
            int[] L2 = { 42, 50, 31 };
            int[] L3 = { 44, 44, 42 };

            if (L1.Length != L2.Length || L2.Length != L3.Length || L1.Length != L3.Length || L3.Length != L2.Length)
            {
                return 0;
            }
            else
            {

                for (int l1i = 0; l1i < L1.Length; l1i++)
                {

                    int l2value = L2[l1i];
                    int l3value = L3[l1i];
                    var result = CompareL1L2L3Value(L1[l1i], l2value, l3value);
                    var resultlow = CompareL1L2L3Value(L1[l1i], l2value, l3value, false);
                    if (result.Key == 1)
                    {
                        if (resultlow.Key == 2)
                        {
                            Console.WriteLine("Matched List {0} with value {1}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, L1[l1i], l1i, CompareL1L2L3Value(L1[l1i], l2value, l3value, false), l2value);

                        }
                        if (resultlow.Key == 3)
                        {
                            Console.WriteLine("Matched List {0} with value {1}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, L1[l1i], l1i, CompareL1L2L3Value(L1[l1i], l2value, l3value, false), l3value);

                        }

                    }
                    if (result.Key == 2)
                    {
                        if (resultlow.Key == 1)
                        {
                            Console.WriteLine("Matched List {0} with value {2}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, l2value, l1i, CompareL1L2L3Value(L2[l1i], l2value, l3value, false), L2[l1i]);

                        }
                        if (resultlow.Key == 3)
                        {
                            Console.WriteLine("Matched List {0} with value {2}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, l2value, l1i, CompareL1L2L3Value(L2[l1i], l2value, l3value, false), l3value);

                        }

                    }
                    if (result.Key == 3)
                    {
                        if (resultlow.Key == 2)
                        {
                            Console.WriteLine("Matched List {0} with value {3}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, l3value, l1i, CompareL1L2L3Value(L3[l1i], l2value, l3value, false), l2value);

                        }
                        if (resultlow.Key == 1)
                        {
                            Console.WriteLine("Matched List {0} with value {3}  : Variable is : {2} at index {3} - Lowest Is {4} found value {5}", result.Key, result.Value, l3value, l1i, CompareL1L2L3Value(L3[l1i], l2value, l3value, false), L2[l1i]);

                        }

                    }
                }

            }
            return 0;
        }

        static void FollowTrend()
        {
            bool privotalpoint = false;
            bool inversalpivot = false;
            decimal HighInCycle = 0;
            decimal LowInCycle = 9999;
            double lastweight = 0;
            bool pivoted = false;

            var client = new CryptoCompareClient();
            //var eth = client.Coins.SnapshotFullAsync(7605).Result;
            var btc = client.History.HourAsync("BTC", "EUR", 1440, new string[] { "Kraken" }, new DateTimeOffset(DateTime.Now)).Result;
            var History = new Stack<Tuple<double, DateTime, Tendance, int>>();
            List<double> InitialValue = new List<double>();
            List<double> CompletValue = new List<double>();
            bool hasbough = false;
            List<Tuple<double, Tendance>> MovingLogic = new List<Tuple<double, Tendance>>();
            List<Tuple<double, Tendance, bool>> Historical = new List<Tuple<double, Tendance, bool>>();

            bool trenddown = false;
            bool trendup = false;
            foreach (var pair in btc.Data)
            {




                //Get Stats

                InitialValue.Add(double.Parse(pair.Open.ToString()));
                CompletValue.Add(double.Parse(pair.Close.ToString()));


                // Identify Moving Logic 

                var FixedIndex = btc.Data.ToList().IndexOf(pair);

                if (FixedIndex > 0)
                {
                    var CurrentPairMinussOne = btc.Data[FixedIndex - 1];
                    var CurrentPriceMoveUP = pair.Close > CurrentPairMinussOne.Close;
                    var VolumeVariationMoveLower = pair.VolumeTo > CurrentPairMinussOne.VolumeTo;

                    if (CurrentPriceMoveUP)
                    {

                        MovingLogic.Add(new Tuple<double, Tendance>((double)pair.Open, Tendance.Up));
                        //Console.WriteLine("Price - Move From {0} to {1}", pair.Close, CurrentPairMinussOne.Close);
                    }

                    else
                    {
                        MovingLogic.Add(new Tuple<double, Tendance>((double)pair.Open, Tendance.Down));
                    }
                }



                //High and Low :)
                if (FixedIndex > 30)
                {



                    IList<decimal> FindPeaksHigh(IList<decimal> values, int rangeOfPeaks)
                    {
                        List<decimal> peaks = new List<decimal>();

                        int checksOnEachSide = rangeOfPeaks / 2;
                        for (int i = 0; i < values.Count; i++)
                        {
                            decimal val = values[i];
                            IEnumerable<decimal> range = values;
                            if (i > checksOnEachSide)
                                range = range.Skip(i - checksOnEachSide);
                            range = range.Take(rangeOfPeaks);
                            if (val == range.Max())
                                peaks.Add(val);
                        }
                        return peaks;
                    }

                    IList<decimal> FindPeaksLow(IList<decimal> values, int rangeOfPeaks)
                    {
                        List<decimal> peaks = new List<decimal>();

                        int checksOnEachSide = rangeOfPeaks / 2;
                        for (int i = 0; i < values.Count; i++)
                        {
                            decimal val = values[i];
                            IEnumerable<decimal> range = values;
                            if (i < checksOnEachSide)
                                range = range.Skip(i - checksOnEachSide);
                            range = range.Take(rangeOfPeaks);
                            if (val == range.Min())
                                peaks.Add(val);
                        }
                        return peaks;
                    }

                    var lowestpeak = FindPeaksLow(btc.Data.ToList().GetRange(FixedIndex - 10, 10).Select(y => y.Close).ToList(), 10);
                    var highpeak = FindPeaksHigh(btc.Data.ToList().GetRange(FixedIndex - 10, 10).Select(y => y.Close).ToList(), 10);
                    double median = MyListExtensions.Mean(btc.Data.ToList().GetRange(FixedIndex - 10, 10).Select(y => (double)y.Close).ToList());
                    int xx = Convert.ToInt32(InitialValue.ToList().Mean());

                    double current = double.Parse(pair.Open.ToString()) / InitialValue.ToList().Max() * 100;
                    bool range80 = current >= 80;
                    bool range60 = current >= 60;
                    bool range40 = current >= 40;
                    bool range20 = current >= 20;


                    double CurrentComparedtomedian = InitialValue.ToList().Mean() / double.Parse(pair.Open.ToString()) * 100;
                    double weight = (double)InitialValue.ToList().Mean() / double.Parse(InitialValue.ToList().Max().ToString());


                    double maxval = double.Parse(InitialValue.ToList().Max().ToString());
                    double lowval = double.Parse(InitialValue.ToList().Min().ToString());


                    double weightmovinglow = (double)InitialValue.ToList().Mean() / double.Parse(InitialValue.ToList().Min().ToString());



                    double realmedianweight = (double)InitialValue.ToList().Mean() / (maxval - lowval);


                    var weightforcegoingdown = weight < lastweight;


                    Console.WriteLine("High Range weight :" + weight);
                    Console.WriteLine("low Range weight :" + weightmovinglow);
                    Console.WriteLine("mid Range weight :" + realmedianweight);

                    //double median = InitialValue.ToList().Mean();
                    double result = Math.Abs(double.Parse(pair.Open.ToString()) - median);
                    double PercentOfVariationFromMedian = double.Parse(pair.Open.ToString()) / median;
                    double MissingPointBetweenMedian = xx - double.Parse(pair.Open.ToString());



                    double resuslt = PercentOfVariationFromMedian / 2;
                    bool orientationforce = resuslt < weight / 2;
                    double implementedvariation = MissingPointBetweenMedian / median * 100;
                    var stddev = GetStandardDeviation(btc.Data.ToList().GetRange(FixedIndex - 10, 10).Select(y => (double)y.Close).ToList());
                    var lowsma9 = MovingAverage(9, btc.Data.ToList().GetRange(FixedIndex - 10, 10).Select(y => (double)y.Close).ToArray());
                    var lowsma15 = MovingAverage(15, btc.Data.ToList().GetRange(FixedIndex - 16, 16).Select(y => (double)y.Close).ToArray());
                    var lowsma25 = MovingAverage(25, btc.Data.ToList().GetRange(FixedIndex - 26, 26).Select(y => (double)y.Close).ToArray());

                    var CandleType = (pair.Low + pair.Close + pair.High) / 3;

                    Console.WriteLine("###############################################");
                    Console.WriteLine("Current Cycle Low : {0}", lowestpeak[0]);
                    Console.WriteLine("Candle bellow the lowest : {0}", pair.Close < lowestpeak[0]);
                    Console.WriteLine("STDev :) : {0}", stddev);
                    Console.WriteLine("cycle sma 9 : {0}", lowsma9.Last());
                    Console.WriteLine("cycle sma 15 : {0}", lowsma15.Last());
                    Console.WriteLine("cycle sma 25 : {0}", lowsma25.Last());
                    Console.WriteLine("Bellow HCL Derivation : {0}", CandleType > pair.Close);
                    Console.WriteLine("Bellow 0 line inside cycle : {0}", (double)pair.Close < median);
                    Console.WriteLine("Percent of variation from 0 line : {0}", PercentOfVariationFromMedian);
                    Console.WriteLine("Points missing points to 0 line : {0}", MissingPointBetweenMedian);
                    Console.WriteLine("Deviation weight : {0}", weight);
                    Console.WriteLine("Trend force reducting : {0}", weightforcegoingdown);
                    Console.WriteLine("Deviation position uper or equal 20 : {0}", range20);
                    Console.WriteLine("Deviation position uper or equal 40 : {0}", range40);
                    Console.WriteLine("Deviation position uper or equal 60 : {0}", range60);
                    Console.WriteLine("Deviation position uper or equal 80 : {0}", range80);
                    Console.WriteLine("Current Price : {0}", pair.Close);
                    Console.WriteLine("Current Cycle High : {0}", highpeak[0]);
                    Console.WriteLine("###############################################");

                    Console.ReadKey();
                    //foreach (var oldc in btc.Data.ToList().GetRange(FixedIndex - 10,10))
                    //{
                    //    if(oldc.Close < LowInCycle)
                    //    {
                    //        LowInCycle = oldc.Close;
                    //        Console.WriteLine("Lowest in cycle = {0}", LowInCycle);

                    //    }
                    //    if (oldc.Close > HighInCycle)
                    //    {
                    //        Console.WriteLine("Highest in cycle = {0}", HighInCycle);
                    //        HighInCycle = oldc.Close;
                    //    }
                    //}

                    lastweight = weight;

                }


            }


        }

        static void Main(string[] args)
        {
            GetOurTrendBitchWithIndex();

            //FollowTrend();

            //bool privotalpoint = false;
            //bool inversalpivot = false;
            //var client = new CryptoCompareClient();
            ////var eth = client.Coins.SnapshotFullAsync(7605).Result;
            //var btc = client.History.HourAsync("BTC", "EUR", 1440, new string[] { "Kraken" }, new DateTimeOffset(DateTime.Now)).Result;
            //var History = new Stack<Tuple<double, DateTime, Tendance, int>>();
            //List<double> InitialValue = new List<double>();
            //List<double> CompletValue = new List<double>();
            //bool hasbough = false;  
            //List<Tuple<double, Tendance>> MovingLogic = new List<Tuple<double, Tendance>>();
            //List<Tuple<double, Tendance, bool>> Historical = new List<Tuple<double, Tendance, bool>>();
            //foreach (var pair in btc.Data)
            //{
            //    InitialValue.Add(double.Parse(pair.Open.ToString()));
            //    CompletValue.Add(double.Parse(pair.Close.ToString()));

            //    int xx = Convert.ToInt32(InitialValue.ToList().Mean());

            //    double current = double.Parse(pair.Open.ToString()) / InitialValue.ToList().Max() * 100;
            //    double CurrentComparedtomedian = InitialValue.ToList().Mean() / double.Parse(pair.Open.ToString()) * 100;
            //    double weight = (double)InitialValue.ToList().Mean() / double.Parse(InitialValue.ToList().Max().ToString());

            //    // Identify Moving Logic 
            //    bool? IsLowerMedian = current < 50;
            //    if (IsLowerMedian.Value == true)
            //    { MovingLogic.Add(new Tuple<double, Tendance>((double)pair.Open, Tendance.Down)); }
            //    if (IsLowerMedian.Value != true)
            //    { MovingLogic.Add(new Tuple<double, Tendance>((double)pair.Open, Tendance.Up)); }

            //    bool? Reached95 = current >= 95;


            //    double median = InitialValue.ToList().Mean();
            //    double result = Math.Abs(double.Parse(pair.Open.ToString()) - median);
            //    double PercentOfVariationFromMedian = double.Parse(pair.Open.ToString()) / median;
            //    double MissingPointBetweenMedian = xx - double.Parse(pair.Open.ToString());


            //    //Display

            //    double resuslt = PercentOfVariationFromMedian / 2;
            //    bool orientationforce = resuslt < weight / 2;
            //    double implementedvariation = MissingPointBetweenMedian / median * 100;
            //    int valueinarray = InitialValue.ToList().IndexOf(double.Parse(pair.Open.ToString()));
            //    if (InitialValue.IndexOf((double)pair.Open) != 0)
            //    {
            //        double precedentvalue = InitialValue[valueinarray - 1];
            //        double MissingPointBetweenMedianOnVal = xx - precedentvalue;
            //        double implementedvariationbefore = MissingPointBetweenMedianOnVal / median * 100;
            //        double Percentvariationonbefore = implementedvariationbefore - implementedvariation;
            //        bool historyAvailable = false;
            //        Tuple<double, Tendance, bool> LastEntrie = null;
            //        if (Historical.Count > 0 & precedentvalue != double.NaN)
            //        {
            //            try
            //            {
            //                var HistoryOld = Historical.Where(y => y.Item1 == precedentvalue).First() ?? null;
            //                historyAvailable = true;
            //                LastEntrie = HistoryOld;

            //            }
            //            catch
            //            {

            //            }
            //        }

            //        if (Percentvariationonbefore < 0)
            //        {
            //            History.Push(new Tuple<double, DateTime, Tendance, int>((double)pair.Open, DateTime.Parse(pair.Time.ToString()), Tendance.Down, 0));
            //            Historical.Add(new Tuple<double, Tendance, bool>((double)pair.Open, Tendance.Down, false));
            //        }
            //        else
            //        {
            //            if (historyAvailable)
            //            {
            //            }
            //            Historical.Add(new Tuple<double, Tendance, bool>((double)pair.Open, Tendance.Up, true));
            //            History.Push(new Tuple<double, DateTime, Tendance, int>((double)pair.Open, DateTime.Parse(pair.Time.ToString()), Tendance.Up, 0));

            //        }


            //        int TendanceSince = 0;
            //        if (History.ToList().Count() > 1)
            //        {
            //            Tendance currnt = History.ToList().FirstOrDefault().Item3;

            //            foreach (var entry in History)
            //            {
            //                if (entry.Item3 == currnt)
            //                {

            //                    TendanceSince++;
            //                    privotalpoint = true;
            //                }
            //                else
            //                {

            //                    int currentindexposition = InitialValue.IndexOf((double)pair.Open);
            //                    var trendbefore = History.ToArray()[currentindexposition - 1];
            //                    if(currnt == Tendance.Down && trendbefore.Item3 == Tendance.Up && hasbough == false)
            //                    {
            //                        hasbough = true;
            //                        //Console.WriteLine("Switched from {0} - to {1}", currnt, trendbefore);
            //                        Console.WriteLine("Buy point : {0}", pair.Open);
            //                    }
            //                    if(currnt == Tendance.Up && trendbefore.Item3 == Tendance.Down && hasbough)
            //                    {
            //                        hasbough = false;
            //                        //Console.WriteLine("Switched from {0} - to {1}", currnt, trendbefore);
            //                        Console.WriteLine("Sell  point : {0}", pair.Open);
            //                        Console.ReadKey();

            //                    }


            //                    break;

            //                }

            //            }
            //        }
            //        if (TendanceSince != 0)
            //        {
            //            if (privotalpoint)
            //            {
            //                privotalpoint = false;
            //            }
            //            var item = History.FirstOrDefault();
            //            History.Pop();
            //            History.Push(new Tuple<double, DateTime, Tendance, int>(item.Item1, item.Item2, item.Item3, TendanceSince));
            //        }

            //        var Group = History.ToList().GroupBy(y => y.Item4);


            //    }
            //    foreach (var entry in History)
            //    {

            //        //Console.WriteLine("Point : {0} - Time {1} - Tendance {2} - Occurence {3}", entry.Item1, entry.Item2, entry.Item3, entry.Item4);
            //    }
            //    var GroupPerHour = History.GroupBy(y => y.Item2.Minute);
            //    int GlobalTendeanceUP = 0;
            //    int GlobalTendeanceDown = 0;
            //    foreach (var perhourentry in GroupPerHour)
            //    {
            //        foreach (var entry in perhourentry)
            //        {
            //            //Console.WriteLine("Point : {0} - Time {1} - Tendance {2} - Occurence {3}", entry.Item1, entry.Item2, entry.Item3, entry.Item4);
            //            if (entry.Item3 == Tendance.Up) { GlobalTendeanceUP++; }
            //            if (entry.Item3 == Tendance.Down) { GlobalTendeanceDown++; }
            //        }
            //        if (perhourentry.Key == DateTime.Now.Minute)
            //        {
            //            //Console.WriteLine("Last Min : {0} has {1} Up and {2} Down", perhourentry.Key, GlobalTendeanceUP, GlobalTendeanceDown);

            //        }
            //        //Console.WriteLine("Last Min : {0} has {1} Up and {2} Down", perhourentry.Key, GlobalTendeanceUP, GlobalTendeanceDown);
            //        if (GlobalTendeanceUP < GlobalTendeanceDown)
            //        {
            //            //Console.WriteLine("Min : {0} is going down ", perhourentry.Key);
            //        }
            //        else
            //        {
            //            //Console.WriteLine("Min : {0} is going up ", perhourentry.Key);
            //        }
            //    }
            //}




        }
    }
}
