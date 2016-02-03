#***************************************************************************************
# MotionBuilder Script that evaluates the quality of a recording of optical markers.
#
# USAGE:
# 1. Import C3D file
# 2. Execute the script within MotionBuilder
# 3. Output will be in the python console for the time being
#
# TODO This script executes really slow and ideally has to be optimized.
#***************************************************************************************

# Import MotionBuilder libraries
from pyfbsdk import *
#from pyfbsdk_additions import *

'''
# For later use to get a better comprehension where the markers belong on our suit
topologyMap = {
    #Body part:     [Markers]
    'Hips':         ["M008","M009","M030","M031"],
    'LeftUpLeg':    ["M029"],
    'LeftLeg':      ["M027","M028"],
    'LeftFoot':     ["M024","M025","M026"],
    'RightUpLeg':   ["M032"],
    'RightLeg':     ["M033","M034"],
    'RightFoot':    ["M035","M036","M037"],
    'Back':         ["M006","M007"],
    'Chest':        ["M004","M005"],
    'LeftArm':      ["M010","M011"],
    'LeftForeArm':  ["M012","M013"],
    'LeftHand':     ["M014","M015","M016"],
    'RightArm':     ["M017","M018"],
    'RightForeArm': ["M019","M020"],
    'RightHand':    ["M021","M022","M023"],
    'Head':         ["M000","M001","M002","M003"]
}
'''

# Will contain results of the evaluation
markerData = {}

###############################################################
# Function(s).                                                #
###############################################################
def evaluateOpticalData(opticalModel):
    global markerData

    takeStart = FBSystem().CurrentTake.LocalTimeSpan.GetStart().GetSecondDouble()
    takeStop = FBSystem().CurrentTake.LocalTimeSpan.GetStop().GetSecondDouble()
    takeDuration = FBSystem().CurrentTake.LocalTimeSpan.GetDuration().GetSecondDouble()

    markerSegments = {}
    # List of segments (recorded data). Each segment belongs to a marker.
    # Which markers do the segments belong to?
    for segment in opticalModel.Segments:
        markerName = segment.Marker.Name
        if markerName in markerSegments:
            markerSegments[markerName].append(segment)
        else:
            entry = {markerName: [segment]}
            markerSegments.update(entry)

    # We got the segments for each marker, now get the gaps inbetween them
    markerGaps = {}
    for marker in markerSegments:
        entry = {marker: []}
        markerGaps.update(entry)

        lastStop = takeStart
        for seg in markerSegments[marker]:
            currentStart = seg.TimeSpan.GetStart().GetSecondDouble()
            gap = currentStart - lastStop
            if gap > 0:
                markerGaps[marker].append(gap)
            # Remember end of current segment for next iteration.
            lastStop = seg.TimeSpan.GetStop().GetSecondDouble()

        #TODO: If gap is before end of take, add it.

    # Compute results and put them in a Dictionary.
    gapCounts = []
    meanGapLengths = []
    maxGapLengths = []
    missingDataList = []
    for marker in markerGaps:
        gapCount = len(markerGaps[marker])
        gapCounts.append(gapCount)
        absoluteGapLength = sum(markerGaps[marker])
        if gapCount > 0:
            meanGapLength =  absoluteGapLength / gapCount
            meanGapLengths.append(meanGapLength)
            maxGapLength = max(markerGaps[marker])
            maxGapLengths.append(maxGapLength)
        else:
            meanGapLength = 0.0
            maxGapLength = 0.0

        # relative amount of missing data
        missingData = absoluteGapLength / takeDuration
        missingDataList.append(missingData)

        # Update Dictionary
        entry = {marker: [gapCount, meanGapLength, maxGapLength, missingData]}
        markerData.update(entry)

    totalGapCount = sum(gapCounts)
    if len(markerGaps) > 0:
        totalMeanGapLength = sum(meanGapLengths)/len(markerGaps)
        maxGapLength = max(maxGapLengths)
        totalMissingData = sum(missingDataList)/len(missingDataList)
    entry = {'Total': [totalGapCount, totalMeanGapLength, maxGapLength, totalMissingData]}
    markerData.update(entry)

###############################################################
# Main.                                                       #
###############################################################
def main():
    global markerData
    if len(FBSystem().Scene.ModelOpticals) > 0:
        evaluateOpticalData(FBSystem().Scene.ModelOpticals[0])
        print("marker: [gapCount, meanGapLength, maxGapLength, missingData]")
        for marker,data in sorted(markerData.iteritems()):
            print(marker,data)
    else:
        FBMessageBox("Message", "No optical model found. Import optical data first.", "Ok")

# This is actually where the script starts.
# check namespace
if __name__ in ('__main__', '__builtin__'):

    main()
