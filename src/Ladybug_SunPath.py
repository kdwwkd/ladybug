﻿# this script is based on RADIANCE sun.c script
# By Mostapha Sadeghipour Roudsari
# Sadeghipour@gmail.com
# Ladybug started by Mostapha Sadeghipour Roudsari is licensed
# under a Creative Commons Attribution-ShareAlike 3.0 Unported License.

"""
This component draws the sun-path, and outputs sun vectors that can be used for sunlight hours analysis
The sun-path Class is a Python version of RADIANCE sun-path script by Greg Ward. RADIANCE source code can be accessed at:
http://www.radiance-online.org/download-install/CVS%20source%20code

-
Provided by Ladybug 0.0.35
    
    Args:
        north: Input a number or a vector to set north; default is set to the Y-axis
        latitude: Input latitude from Import .epw component
        longtitude:  Input longtitude. You can find it from location output from Import .epw component
                     longtitude and timeZone will be used for time correction.
        timeZone:  Input timeZone. You can find it from location output from Import .epw component
                     longtitude and timeZone will be used for time correction.
        hour: Input a list of numbers to indicate hours; default is 12:00 [1-24]
        day: Input a list of numbers to indicate days; default is 21 [1-31]
        month: Input a list of numbers to indicate months; default is 12 [1-12]
        timeStep: Number of timesteps per hour. The number should be smaller than 60 and divisible into 60. Default is 1
                  A linear interpolation for data overlay will be applied for timeSteps more than 1
        analysisPeriod: [optional] Analysis period from Analysis Period component; may be used to override hour, day and month input
        centerPt: Input a point to locate the center point of the sun-path
        sunPathScale: Input a number to set the scale of the sun-path
        sunScale: Input a number to set the scale of sun spheres
        ---------------- : This is just for graphical purpose. I appreciate your curiosity though!
        annualHourlyData: Connect a list of annual hourly data to be overlaid on sunpath
        conditionalStatement: The Conditional Statement Input allows users to filter data for specific conditions. Specific hourly data, such as temperature or humidity, can be filtered and overlaid with the Sun Path. The conditional statement should be a valid condition statement in Python such as a>25 and b<80.
                              The current version accepts "and" and "or" operators. To visualize the hourly data, only lowercase English letters should be used as variables, and each letter corresponds to each of the lists (in their respective order): "a" always represents the 1st list, "b" represents the 2nd list, etc.
                              For example, if you have hourly dry bulb temperature connected as the first list, and relative humidity connected as the second list, and you want to plot the data for the time period when temperature is between 18 and 23, and humidity is less than 80%, the statement should be written as “18<a<23 and b<80” (without quotation marks)
        legendPar: Input legend parameters from the Ladybug Legend Parameters component
        dailySunPath: Set Boolean to True to visualize the daily sun-path
        annualSunPath: Set Boolean to True to visualize the annual sun-path
        bakeIt: Set to True to bake the sunpath
    Returns:
        report: Report!!!
        sunSpheresMesh: Colored sun mesh spheres as a joined mesh
        sunPositions: A list of points for sun positions
        sunVectors: Sun vectors
        sunAltitudes: A list of numbers for sun altitudes in degrees
        sunAzimuths: A list of numbers for sun azimuths in degrees
        sunPathCrvs: Sun-path curves
        --------------: This is just for graphical purpose. I appreciate your curiosity though!
        legend: Legend(s) of the chart(s). Connect to Geo for preview
        legendBasePts: Legend base points, mainly for presentation purposes 
        sunPathCenPts: Center points of the sun-path, mainly for presentation purposes 
        sunPositionsInfo: Information for each sun position 
        selHourlyData: Selected hourly data from the annual hourly data
"""

ghenv.Component.Name = "Ladybug_SunPath"
ghenv.Component.NickName = 'sunPath'
ghenv.Component.Message = 'VER 0.0.35\nJAN_03_2013'

import math
import System
import rhinoscriptsyntax as rs
import Rhino as rc
import scriptcontext as sc
from clr import AddReference
AddReference ('Grasshopper')
import Grasshopper.Kernel as gh
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

def checkConditionalStatement(annualHourlyData, conditionalStatement):
        lb_preparation = sc.sticky["ladybug_Preparation"]()
        indexList, listInfo = lb_preparation.separateList(annualHourlyData, lb_preparation.strToBeFound)
        
        letters = [chr(i) for i in xrange(ord('a'), ord('z')+1)]
        # remove 'and' and 'or' from conditional statements
        csCleaned = conditionalStatement.replace('and', '',20000)
        csCleaned = csCleaned.replace('or', '',20000)
        
        # find the number of the lists that have assigned conditional statements
        listNum = []
        for count, let in enumerate(letters):
            if csCleaned.find(let)!= -1: listNum.append(count)
        
        # check if all the conditions are actually applicable
        for num in listNum:
            if num>len(listInfo) - 1:
                warning = 'A conditional statement is assigned for list number ' + `num + 1` + '  which is not existed!\n' + \
                          'Please remove the letter "' + letters[num] + '" from the statements to solve this problem!\n' + \
                          'Number of lists are ' + `len(listInfo)` + '. Please fix this issue and try again.'
                          
                print warning
                ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, warning)
                return -1, -1
        
        selList = []
        [selList.append([]) for i in range(len(listInfo))]
        for i in range(len(listInfo)):
            selList[i] = annualHourlyData[indexList[i]+7:indexList[i+1]]
            if listInfo[i][4]!='Hourly' or listInfo[i][5]!=(1,1,1) or  listInfo[i][6]!=(12,31,24) or len(selList[i])!=8760:
                warning = 'At least one of the input data lists is not a valis ladybug hourly data! Please fix this issue and try again!\n List number = '+ `i+1`
                print warning
                ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, warning)
                return -1, -1
        
        # replace the right list in the conditional statement
        statement = conditionalStatement.split(' ')
        finalStatement = 'pattern = '
        titleStatement = '...                         ...                         ...\n' +\
                         'Conditiontional Selection Applied:\n'
        
        for statemntPart in statement:
            statementCopy = str.Copy(statemntPart) # a copy to make a meaningful string
            
            if statemntPart!='and' and statemntPart!='or':
                for num in listNum:
                    toBeReplacedWith = 'selList[this][HOY]'.replace('this', `num`)
                    titleToBeReplacedWith = listInfo[num][2]
                    
                    statemntPart = statemntPart.replace(letters[num], toBeReplacedWith, 20000)
                    statementCopy = statementCopy.replace(letters[num], titleToBeReplacedWith, 20000)
                    if statementCopy.find(letters[num])!=-1: break
                    
                titleStatement = titleStatement + ' ' + statementCopy
            else:
                
                titleStatement = titleStatement + '\n' + statementCopy
            finalStatement = finalStatement + ' ' + statemntPart
        print titleStatement
        
        # check for the pattern
        patternList = []
        try:
            for HOY in range(8760):
                exec(finalStatement)
                patternList.append(pattern)
        except Exception,e:
            warning = 'There is an error in the conditional statement:\n' + `e`
            print warning
            ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, warning)
            return -1, -1
        
        return titleStatement, patternList

def main(latitude, longtitude, timeZone, dailySunPath, annualSunPath, timeStep, hour, day, month):
    # import the classes
    if sc.sticky.has_key('ladybug_release'):
        lb_preparation = sc.sticky["ladybug_Preparation"]()
        lb_visualization = sc.sticky["ladybug_ResultVisualization"]()
        lb_sunpath = sc.sticky["ladybug_SunPath"]()
        
        conversionFac = lb_preparation.checkUnits()
        def colorSun(spheres, colors):
            sunS = rc.Geometry.Mesh()
            repeatedColors = []
            for j, sun in enumerate(spheres):
                for face in range(sun.Faces.Count):repeatedColors.append(colors[j])
                sunS.Append(sun)
            return lb_visualization.colorMesh(repeatedColors, sunS)

        def bakePlease(listInfo, sunsJoined, legendSrfs, legendText, textPt, textSize, sunPathCrvs):
            # legendText = legendText + ('\n\n' + customHeading)
            studyLayerName = 'SUNPATH'
            try:
                layerName = listInfo[1]
                dataType = 'Hourly Data:' + listInfo[2]
            
            except:
                layerName = 'Latitude=' +`latitude`
                dataType = 'No Hourly Data'
            
            # check the study type
            newLayerIndex, l = lb_visualization.setupLayers(dataType, 'LADYBUG', layerName, studyLayerName)
            lb_visualization.bakeObjects(newLayerIndex, sunsJoined, legendSrfs, legendText, textPt, textSize, 'Verdana', sunPathCrvs)
        
        def movePointList(textPt, movingVector):
            for ptCount, pt in enumerate(textPt):
                ptLocation = rc.Geometry.Point(pt)
                ptLocation.Translate(movingVector) # move it to the right place
                textPt[ptCount] = rc.Geometry.Point3d(ptLocation.Location)
            return textPt


        # define sun positions based on altitude and azimuth [this one should have a bug]
        sunPositions = []; sunVectors = []; sunUpHours = []; sunSpheres = []
        sunAlt = []; sunAzm = []; sunPosInfo = []
        PI = math.pi;

        northAngle, northVector = lb_preparation.angle2north(north)
        
        cenPt = lb_preparation.getCenPt(centerPt)
        scale = lb_preparation.setScale(sunPathScale, conversionFac) * 200
        sunSc = lb_preparation.setScale(sunScale, conversionFac)* scale * conversionFac * 0.007
        
        try:
            timeStep = int(timeStep)
            if 60%timeStep!=0:
                validTimeSteps = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60]
                stepDifference = []
                [stepDifference.append(abs(validTimeStep - timeStep)) for validTimeStep in validTimeSteps]
                timeStep = validTimeSteps[stepDifference.index(min(stepDifference))]
                print 'Time-step is set to ' + `timeStep`
        except: timeStep = 1; print 'Time-step is set to 1'
        
        if longtitude!=None and timeZone != None:
            try: longtitude = float(longtitude); timeZone = float(timeZone)
            except: longtitude = 0; timeZone = 0
        else: longtitude = 0; timeZone = 0
        
        # look for analysisPeriod
        if len(analysisPeriod)!=0 and analysisPeriod[0]!=None:
            stMonth, stDay, stHour, endMonth, endDay, endHour = lb_preparation.readRunPeriod(analysisPeriod, True, False)
            
            days = range(32)
            
            if stMonth > endMonth: months = orange(stMonth, 13) + range(1, endMonth + 1)
            else: months = range(stMonth, endMonth + 1)
            hour  = range(stHour, endHour)
        else:
            days = day
            months = month
            
        if timeStep != 1: hours = rs.frange(hour[0], hour[-1] + 1 - 1/timeStep, 1/timeStep)
        else: hours = hour
        
        
        if latitude!=None:
            # check conditional statement for the whole year
            titleStatement = -1
            if conditionalStatement and len(annualHourlyData)!=0 and annualHourlyData[0]!=None:
                print 'Checking conditional statements...'
                # send all data and statement to a function and return back
                # True, False Pattern and condition statement
                titleStatement, patternList = checkConditionalStatement(annualHourlyData, conditionalStatement)
            
            if titleStatement == -1:
                patternList = [[True]] * 8760
                titleStatement = False

            printWarning = False
            if float(latitude) > 90: latitude = 90; printWarning = True
            elif float(latitude) < -90: latitude = -90; printWarning = True
                
            if printWarning == True:
                print 'Latitude should be between -90 and 90'
                w = gh.GH_RuntimeMessageLevel.Warning
                ghenv.Component.AddRuntimeMessage(w, 'Latitude should be between -90 and 90')
            
            
            lb_sunpath.initTheClass(float(latitude), northAngle, cenPt, scale, longtitude, timeZone)
            # count total sun up hours
            SUH = 0
            for m in months:
                for d in days:
                    for h in hours:
                        h = lb_preparation.checkHour(float(h))
                        m  = lb_preparation.checkMonth(int(m))
                        d = lb_preparation.checkDay(int(d), m)
                        lb_sunpath.solInitOutput(m, d, h)
                        if lb_sunpath.solAlt >= 0: SUH += 1
                        if lb_sunpath.solAlt >= 0 and patternList[int(round(lb_preparation.date2Hour(m, d, h)))]:
                            sunSphere, sunVector, sunPoint = lb_sunpath.sunPosPt(sunSc)
                            # find the hour of the year
                            sunUpHours.append(lb_preparation.date2Hour(m, d, h))
                            sunPosInfo.append(lb_preparation.hour2Date(lb_preparation.date2Hour(m, d, h)))
                            sunPositions.append(sunPoint)
                            sunSpheres.append(sunSphere)
                            sunVectors.append(sunVector)
                            sunAlt.append(math.degrees(lb_sunpath.solAlt))
                            sunAzm.append(math.degrees(lb_sunpath.solAz))
            # create sun-path geometry
            #if annualSunPath!=False: dailySunPath=False
            #if dailySunPath!=False: annualSunPath=False
            
            dailySunPathCrvs = []
            annualSunPathCrvs = []
            baseCrvs = []
            if annualSunPath!=False:
                annualSunPathCrvs = [item.ToNurbsCurve() for sublist in lb_sunpath.drawSunPath() for item in sublist]
            if dailySunPath: dailySunPathCrvs = lb_sunpath.drawDailyPath(m, d).ToNurbsCurve()
            if annualSunPath or dailySunPath: baseCrvs = [rc.Geometry.Circle(cenPt, 1.08*scale).ToNurbsCurve()] #lb_sunpath.drawBaseLines()
        
            sunPathCrvs = []
            if annualSunPathCrvs: sunPathCrvs = sunPathCrvs + annualSunPathCrvs
            if dailySunPathCrvs: sunPathCrvs = sunPathCrvs + [dailySunPathCrvs]
            if baseCrvs: sunPathCrvs = sunPathCrvs + baseCrvs
            if sunPathCrvs!=[]: lb_visualization.calculateBB(sunPathCrvs, True)
            # sunPathCrvs = sunPathCrvs - baseCrvs
            overwriteScale = False
            if legendPar == []: overwriteScale = True
            elif legendPar[-1] == []: overwriteScale = True
            lowB, highB, numSeg, customColors, legendBasePoint, legendScale = lb_preparation.readLegendParameters(legendPar, False)
            
            if overwriteScale: legendScale = 0.9
            
            
            
            legend = []; legendText = []; textPt = []; legendSrfs = None
            customHeading = '\n\n\n\nSun-Path Diagram - Latitude: ' + `latitude` + '\n'
            colors = [System.Drawing.Color.Yellow] * len(sunPositions)
            
            allSunPositions = []; allSunsJoined = []; allSunVectors = []
            allSunPathCrvs = []; allLegend = []; allValues = []
            allSunAlt = []; allSunAzm = []; cenPts = []; allSunPosInfo = []
            legendBasePoints = []
            # hourly data
            if len(annualHourlyData)!=0 and annualHourlyData[0]!=None:
                try: movingDist = 1.5 * lb_visualization.BoundingBoxPar[1] # moving distance for sky domes
                except: movingDist = 0
                
                #separate data
                indexList, listInfo = lb_preparation.separateList(annualHourlyData, lb_preparation.strToBeFound)
                
                for i in range(len(listInfo)):
                    movingVector = rc.Geometry.Vector3d(i * movingDist, 0, 0)
                    values= []
                    selList = [];
                    modifiedsunPosInfo = []
                    [selList.append(float(x)) for x in annualHourlyData[indexList[i]+7:indexList[i+1]]]
                    if listInfo[i][4]!='Hourly' or listInfo[i][5]!=(1,1,1) or  listInfo[i][6]!=(12,31,24) or len(selList)!=8760:
                        warning = 'At least one of the input data lists is not a valis ladybug hourly data! Please fix this issue and try again!\n List number = '+ `i+1`
                        print warning
                        ghenv.Component.AddRuntimeMessage(gh.GH_RuntimeMessageLevel.Warning, warning)
                        return -1
                    else:
                        #find the numbers
                        for h, hr in enumerate(sunUpHours):
                            value = selList[int(math.floor(hr))] + (selList[int(math.ceil(hr))] - selList[int(math.floor(hr))])* (hr - math.floor(hr))
                            values.append(value)
                            modifiedsunPosInfo.append(sunPosInfo[h] + '\n' + ("%.2f" % value) + ' ' + listInfo[i][3])
                    if values!=[] and sunPathCrvs!=[]:
                        # mesh colors
                        colors = lb_visualization.gradientColor(values, lowB, highB, customColors)
                        
                        customHeading = '\n\n\n\nSun-Path Diagram - Latitude: ' + `latitude` + '\n'
                        legendSrfs, legendText, legendTextCrv, textPt, textSize = lb_visualization.createLegend(values
                                , lowB, highB, numSeg, listInfo[i][3], lb_visualization.BoundingBoxPar, legendBasePoint, legendScale)
                        
                        # generate legend colors
                        legendColors = lb_visualization.gradientColor(legendText[:-1], lowB, highB, customColors)
                        
                        # color legend surfaces
                        legendSrfs = lb_visualization.colorMesh(legendColors, legendSrfs)
                        
                        # list info should be provided in case there is no hourly input data
                        
                        if len(sunSpheres) == 1:
                            customHeading = customHeading + '\n' + lb_preparation.hour2Date(lb_preparation.date2Hour(m, d, h)) + \
                                           ', ALT = ' + ("%.2f" % sunAlt[0]) + ', AZM = ' + ("%.2f" % sunAzm[0]) + '\n'
                        elif len(months) == 1 and len(days) == 1:
                            customHeading = customHeading + '\n' + `days[0]` + ' ' + lb_preparation.monthList[months[0] -1] + '\n'
                        
                        customHeading = customHeading + 'Hourly Data: ' + listInfo[i][2] + ' (' + listInfo[i][3] + ')\n' + listInfo[i][1]
                        
                        if titleStatement:
                            resultStr = ("%.1f" % (len(values)/timeStep)) + ' hours of total ' + ("%.1f" % (SUH/timeStep)) + ' sun up hours' + \
                                        '(' + ("%.2f" % ((len(values)/timeStep)/(SUH/timeStep) * 100)) + '%).'
                            # print resultStr
                            customHeading = customHeading + '\n' + titleStatement + '\n' + resultStr
                        
                        titleTextCurve, titleStr, titlebasePt = lb_visualization.createTitle([listInfo[i]], lb_visualization.BoundingBoxPar, legendScale, customHeading, True)
                        
                        
                        legend = lb_visualization.openLegend([legendSrfs, [lb_preparation.flattenList(legendTextCrv + titleTextCurve)]])
                        
                        legendText.append(titleStr)
                        textPt.append(titlebasePt)
                        
                        sunsJoined = colorSun(sunSpheres, colors)
                        
                        ##
                        compassCrvs, compassTextPts, compassText = lb_visualization. compassCircle(cenPt, northVector, scale, range(0, 360, 30), 1.5*textSize)
                        numberCrvs = lb_visualization.text2crv(compassText, compassTextPts, 'Times New Romans', textSize/1.5)
                        compassCrvs = compassCrvs + lb_preparation.flattenList(numberCrvs)
                    

                        # let's move it move it move it!
                        if legendScale>1: movingVector = legendScale * movingVector
                        sunsJoined.Translate(movingVector); allSunsJoined.append(sunsJoined)
                        
                        textPt = movePointList(textPt, movingVector)
                        
                        sunPosDup = []
                        [sunPosDup.append(pt) for pt in sunPositions]
                        allSunPositions.append(movePointList(sunPosDup, movingVector))
                        
                        newCenPt = movePointList([cenPt], movingVector)[0];
                        cenPts.append(newCenPt)
                        
                        if legendBasePoint == None:
                            nlegendBasePoint = lb_visualization.BoundingBoxPar[0]
                            movedLegendBasePoint = rc.Geometry.Point3d.Add(nlegendBasePoint, movingVector);
                        else:
                            movedLegendBasePoint = rc.Geometry.Point3d.Add(legendBasePoint, movingVector);
                            
                        legendBasePoints.append(movedLegendBasePoint)
                        
                        for crv in legendTextCrv:
                            for c in crv: c.Translate(movingVector)
                        for crv in titleTextCurve:
                            for c in crv: c.Translate(movingVector)
                        crvsTemp = []
                        for c in sunPathCrvs + compassCrvs:
                            cDuplicate = c.Duplicate()
                            cDuplicate.Translate(movingVector)
                            crvsTemp.append(cDuplicate)
                        allSunPathCrvs.append(crvsTemp)
                        
                        legendSrfs.Translate(movingVector)
                        allLegend.append(lb_visualization.openLegend([legendSrfs, [lb_preparation.flattenList(legendTextCrv + titleTextCurve)]]))
                        
                        allSunPosInfo.append(modifiedsunPosInfo)
                        allValues.append(values)
                        
                        if bakeIt: bakePlease(listInfo[i], sunsJoined, legendSrfs, legendText, textPt, textSize, crvsTemp)
            
                return allSunPositions, allSunsJoined, sunVectors, allSunPathCrvs, allLegend, allValues, sunAlt, sunAzm, cenPts, allSunPosInfo, legendBasePoints
            
            # no hourly data tp overlay
            elif dailySunPath or annualSunPath:
                values = []
                if len(sunSpheres) == 1:
                    customHeading = customHeading + '\n' + lb_preparation.hour2Date(lb_preparation.date2Hour(m, d, h)) + \
                                   ', ALT = ' + ("%.2f" % sunAlt[0]) + ', AZM = ' + ("%.2f" % sunAzm[0]) + '\n'
                elif len(months) == 1 and len(days) == 1:
                    customHeading = customHeading + '\n' + `days[0]` + ' ' + lb_preparation.monthList[months[0] -1]
                    
                textSize = legendScale * 0.5 * lb_visualization.BoundingBoxPar[2]/20
                titlebasePt = lb_visualization.BoundingBoxPar[-2]
                titleTextCurve = lb_visualization.text2crv(['\n\n' + customHeading], [titlebasePt], 'Veranda', textSize)
                legend = None, lb_preparation.flattenList(titleTextCurve)
                
                legendText.append('\n\n' + customHeading)
                textPt.append(titlebasePt)
                sunsJoined = colorSun(sunSpheres, colors)
                
                compassCrvs, compassTextPts, compassText = lb_visualization. compassCircle(cenPt, northVector, scale, range(0, 360, 30), 1.5*textSize)
                numberCrvs = lb_visualization.text2crv(compassText, compassTextPts, 'Times New Romans', textSize/1.5)
                compassCrvs = compassCrvs + lb_preparation.flattenList(numberCrvs)
                
                if bakeIt: bakePlease(None, sunsJoined, legendSrfs, legendText, textPt, textSize, sunPathCrvs + compassCrvs)
                
            else: return -1
                
            return [sunPositions], [sunsJoined], sunVectors, [sunPathCrvs + compassCrvs], [legend], [values], sunAlt, sunAzm, [cenPt], [sunPosInfo], [titlebasePt]
        
        else:
            print 'Please input a number for Latitude'
            w = gh.GH_RuntimeMessageLevel.Warning
            ghenv.Component.AddRuntimeMessage(w, "Please input a number for Latitude")
            return -1
    else:
        print "You should first let the Ladybug fly..."
        w = gh.GH_RuntimeMessageLevel.Warning
        ghenv.Component.AddRuntimeMessage(w, "You should first let the Ladybug fly...")
        return -1
        
        
result = main(latitude, longtitude, timeZone, dailySunPath, annualSunPath, timeStep, hour, day, month)

if result!= -1:
    sunPositionsList, sunSpheres, sunVectors, sunPathCrvsList, legendCrvs, selHourlyDataList, sunAltitudes, sunAzimuths, centerPoints, sunPosInfoList,  legendBasePtList= result
    
    # graft the data
    # I added this at the last minute! There should be a cleaner way
    legend = DataTree[System.Object]()
    sunSpheresMesh = DataTree[System.Object]()
    sunPathCrvs = DataTree[System.Object]()
    selHourlyData = DataTree[System.Object]()
    sunPositions = DataTree[System.Object]()
    sunPathCenPts = DataTree[System.Object]()
    sunPositionsInfo = DataTree[System.Object]()
    legendBasePts = DataTree[System.Object]()
    for i, leg in enumerate(legendCrvs):
        p = GH_Path(i)
        legend.Add(leg[0], p)
        legend.AddRange(leg[1], p)
        sunSpheresMesh.Add(sunSpheres[i],p)
        sunPathCrvs.AddRange(sunPathCrvsList[i],p)
        selHourlyData.AddRange(selHourlyDataList[i],p)
        sunPositions.AddRange(sunPositionsList[i],p)
        sunPathCenPts.Add(centerPoints[i],p)
        sunPositionsInfo.AddRange(sunPosInfoList[i], p)
        legendBasePts.Add(legendBasePtList[i],p)
else:
    print 'Set dailySunPath or annualSunPath to True'
    w = gh.GH_RuntimeMessageLevel.Warning
    ghenv.Component.AddRuntimeMessage(w, "Set dailySunPath or annualSunPath to True")