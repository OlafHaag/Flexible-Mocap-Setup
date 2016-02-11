#***************************************************************************************
# Autosetup Actor for Phasespace Suit
#
# REQUIREMENTS: At least 38 optical Markers (C3D or OWL) for performer.
#               Performer should be in a T-pose facing +Z.
#
# USAGE:
# 1. Open FBX with data in it or import C3D, or connect to OWL server
# 4. Load rigid body preset (optional)
# 2. Execute the script
# 4. Adjust fitting if necessary, by unchecking "Active"
# 5. Re-apply the markersets by pressing Snap (recalculate TR)
#
# THINGS TO NOTE:
# * Suit must follow the exact same configuration of markers, or the
#   script will not work.
# * If the Actor already has a Marker Sets attached to it, this will just create
#   a new Marker Set, instead of replacing the one that is already there.
#***************************************************************************************

from pyfbsdk import *
import math

'''---AUTOSETUP FUNCTIONS AND VARIABLES---'''
actor_height = 150.1
actor_armlen = 62.4
actor_fingers = 12.6
# Offsets between hip pivot location and hip marker center
hips_yoffset = 4.5
hips_zoffset = 10.0
# List of actors and markers
markerList = []
rigidBodies = []
actors = []

# Average positions of a set of FBModels to find the center
def findCenter(pts):
    avg_x = 0.0
    avg_y = 0.0
    avg_z = 0.0
    size = len(pts)

    for p in pts:
        p_pos = vector(p)
        avg_x += p_pos[0]
        avg_y += p_pos[1]
        avg_z += p_pos[2]

    avg_x /= size
    avg_y /= size
    avg_z /= size
    return [avg_x, avg_y, avg_z]

# Recursively select markers in scene
def selectMarkers(root):
    if root:
        for child in root.Children:
            if (child.Name.startswith('M') and child.Name.strip('M').isdigit()) or child.Name.startswith('marker_'):
                child.Selected = True
            selectMarkers(child)

# Get position FBVector3d from FBModel m
def vector(m):
    v = FBVector3d()
    m.GetVector(v)
    return v

# Get marker models from IDs
def markers(ids):
    m = []
    for i in ids:
        m.append(markerList[i])
    return m

# Scale FBActor using scale factors for body and arms
def scaleActor(actor, s_factor, ra_factor, la_factor):
    s_vector = FBVector3d(s_factor, s_factor, s_factor)
    ra_vector = FBVector3d(ra_factor, ra_factor, ra_factor)
    la_vector = FBVector3d(la_factor, la_factor, la_factor)
    # Body
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonHipsIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonWaistIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonChestIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonNeckIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonHeadIndex, s_vector)
    # Legs (scaling applied symmetrically, so right side also scales)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftHipIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftKneeIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, s_vector)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftFootIndex, s_vector)
    # Arms are scaled separately from the rest of the body
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftCollarIndex, la_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftShoulderIndex, la_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftElbowIndex, la_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, la_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonRightCollarIndex, ra_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonRightShoulderIndex, ra_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonRightElbowIndex, ra_vector, False)
    actor.SetDefinitionScaleVector(FBSkeletonNodeId.kFBSkeletonRightWristIndex, ra_vector, False)

# Scale and fit Actor to marker cloud
def autofit(actor):
    global markerList
    suitMarkers = 38
    # Find center of hips, hands, and feet
    hips_center = findCenter([markerList[8], markerList[9], markerList[30], markerList[31]])
    lfoot = findCenter([markerList[24], markerList[25], markerList[26]])
    rfoot = findCenter([markerList[35], markerList[36], markerList[37]])
    lhand_center = findCenter([markerList[14], markerList[15], markerList[16]])
    rhand_center = findCenter([markerList[21], markerList[22], markerList[23]])
    # Account for offset between hip points and hip pivot
    hips_center[1] -= hips_yoffset
    hips_center[2] -= hips_zoffset
    # Translate FBActor to hip points
    actor.SetActorTranslation(FBVector3d(hips_center))
    # Find height of performer from ground to shoulder markers and arm length
    ls_pos = vector(markerList[10])
    rs_pos = vector(markerList[17])
    rx_dist = rhand_center[0] - rs_pos[0]
    ry_dist = rhand_center[1] - rs_pos[1]
    rz_dist = rhand_center[2] - rs_pos[2]
    lx_dist = lhand_center[0] - ls_pos[0]
    ly_dist = lhand_center[1] - ls_pos[1]
    lz_dist = lhand_center[2] - ls_pos[2]
    perf_height = (rs_pos[1] + ls_pos[1])/2
    perf_rarmlen = math.sqrt((rx_dist * rx_dist) + (ry_dist * ry_dist) + (rz_dist * rz_dist))
    perf_larmlen = math.sqrt((lx_dist * lx_dist) + (ly_dist * ly_dist) + (lz_dist * lz_dist))
    # Compute scale factor for body and arms
    s_factor = perf_height/actor_height
    rs_factor = perf_rarmlen/actor_armlen
    ls_factor = perf_larmlen/actor_armlen
    # Scale FBActor down or up using scale factor
    scaleActor(actor, s_factor, rs_factor, ls_factor)
    # Compute angular offsets for arms
    actor_army = 149.0 * s_factor
    actor_armz = hips_center[2] + (6.5 * s_factor)
    rarm_roty = math.atan2(rhand_center[2] - actor_armz, rs_pos[0] - rhand_center[0]) * (180/math.pi)
    rarm_rotz = math.atan2(actor_army - rhand_center[1], rs_pos[0] - rhand_center[0]) * (180/math.pi)
    larm_roty = -1 * math.atan2(lhand_center[2] - actor_armz, lhand_center[0] - ls_pos[0]) * (180/math.pi)
    larm_rotz = math.atan2(lhand_center[1] - actor_army, lhand_center[0] - ls_pos[0]) * (180/math.pi)
    # Compute angular offsets for legs
    actor_legx = 9.6 * s_factor
    rfoot = findCenter([markerList[35], markerList[36], markerList[37]])
    rleg = vector(markerList[31])
    rleg_rotz = math.atan2(rfoot[0] - (hips_center[0] - actor_legx), rleg[1] - rfoot[1]) * (180/math.pi)
    lfoot = findCenter([markerList[24], markerList[25], markerList[26]])
    lleg = vector(markerList[30])
    lleg_rotz = math.atan2(lfoot[0] - (hips_center[0] + actor_legx), lleg[1] - lfoot[1]) * (180/math.pi)
    # Rotate FBActor limbs to fit markers
    actor.SetDefinitionRotationVector(FBSkeletonNodeId.kFBSkeletonRightShoulderIndex, FBVector3d(0, rarm_roty, rarm_rotz), False)
    actor.SetDefinitionRotationVector(FBSkeletonNodeId.kFBSkeletonLeftShoulderIndex, FBVector3d(0, larm_roty, larm_rotz), False)
    actor.SetDefinitionRotationVector(FBSkeletonNodeId.kFBSkeletonRightHipIndex, FBVector3d(0, 0, rleg_rotz), False)
    actor.SetDefinitionRotationVector(FBSkeletonNodeId.kFBSkeletonLeftHipIndex, FBVector3d(0, 0, lleg_rotz), False)

# Map markers to Actor markerset
def automap(actor, hasRigidBodies):
    global markerList, rigidBodies

    actor.MarkerSet = FBMarkerSet("Actor_Markers")
    # Head
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHeadIndex, markerList[0])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHeadIndex, markerList[1])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHeadIndex, markerList[2])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHeadIndex, markerList[3])
    # Chest
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonChestIndex, markerList[4])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonChestIndex, markerList[5])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonChestIndex, markerList[6])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonChestIndex, markerList[7])
    # Hips
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHipsIndex, markerList[8])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHipsIndex, markerList[9])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHipsIndex, markerList[30])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHipsIndex, markerList[31])
    # Right Leg
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightHipIndex, markerList[32])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightKneeIndex, markerList[33])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightKneeIndex, markerList[34])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightAnkleIndex, markerList[35])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightAnkleIndex, markerList[36])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightAnkleIndex, markerList[37])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightFootIndex, markerList[36])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightFootIndex, markerList[37])
    # Left Leg
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftHipIndex, markerList[29])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftKneeIndex, markerList[28])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftKneeIndex, markerList[27])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, markerList[26])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, markerList[25])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, markerList[24])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftFootIndex, markerList[24])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftFootIndex, markerList[25])
    # Left Arm
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftCollarIndex, markerList[10])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftShoulderIndex, markerList[11])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftElbowIndex, markerList[12])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftElbowIndex, markerList[13])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, markerList[14])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, markerList[15])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, markerList[16])
    # Right Arm
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightCollarIndex, markerList[17])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightShoulderIndex, markerList[18])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightElbowIndex, markerList[19])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightElbowIndex, markerList[20])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightWristIndex, markerList[21])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightWristIndex, markerList[22])
    actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightWristIndex, markerList[23])

    # Rigid bodies
    if hasRigidBodies:
        # Head
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHeadIndex, rigidBodies[6].Model)
        actor.MarkerSet.SetMarkerOriented(FBSkeletonNodeId.kFBSkeletonHeadIndex, 4, True)
        # Chest
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonChestIndex, rigidBodies[7].Model)
        # Hips
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonHipsIndex, rigidBodies[8].Model)
        # Right Leg
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightKneeIndex, rigidBodies[10].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightAnkleIndex, rigidBodies[12].Model)
        actor.MarkerSet.SetMarkerOriented(FBSkeletonNodeId.kFBSkeletonRightAnkleIndex, 3, True)
        # Left Leg
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftKneeIndex, rigidBodies[9].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, rigidBodies[11].Model)
        actor.MarkerSet.SetMarkerOriented(FBSkeletonNodeId.kFBSkeletonLeftAnkleIndex, 3, True)
        # Right Arm
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightShoulderIndex, rigidBodies[5].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightElbowIndex, rigidBodies[3].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonRightWristIndex, rigidBodies[1].Model)
        actor.MarkerSet.SetMarkerOriented(FBSkeletonNodeId.kFBSkeletonRightWristIndex, 3, True)
        # Left Arm
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftShoulderIndex, rigidBodies[4].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftElbowIndex, rigidBodies[2].Model)
        actor.MarkerSet.AddMarker(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, rigidBodies[0].Model)
        actor.MarkerSet.SetMarkerOriented(FBSkeletonNodeId.kFBSkeletonLeftWristIndex, 3, True)

# Collect markers and check count
def getMarkers():
    global markerList

    # Obtain markers from scene
    markers = FBModelList()
    selectMarkers(FBSystem().Scene.RootModel)
    FBGetSelectedModels(markers)

    # Reverse marker list, so that M000 is first and so on.
    mCount = markers.GetCount()
    mIndex = mCount - 1
    markerList = []
    for i in range(mCount):
        markerList.append(markers[mIndex - i])
    # Check if enough markers were found
    suitMarkers = 38
    if len(markers) < suitMarkers:
        FBMessageBox("Message", "Not enough markers found. There should be at least 38.", "Ok")
        return False
    else:
        return True

def getRigidBodies(opticalRoot):
    global rigidBodies
    if len(opticalRoot.RigidBodies) > 0:
        rigidBodies = opticalRoot.RigidBodies
        return True
    else:
        return False

def createActor(name, hasRigidBodies):
    actor = FBActor(name)
    autofit(actor)
    automap(actor, hasRigidBodies)
    for comp in FBSystem().Scene.Components:
        comp.Selected = False
    actor.Selected = True
    actor.Snap(FBRecalcMarkerSetOffset.kFBRecalcMarkerSetOffsetTR)

###############################################################
# Main.                                                       #
###############################################################
def main():
    if len(FBSystem().Scene.ModelOpticals) > 0:
        optRoot = FBSystem().Scene.ModelOpticals[0]
        if getMarkers():
            if getRigidBodies(optRoot):
                createActor("Performer_Actor", True)
            else:
                lRes = FBMessageBox("Message", "No rigid bodies found. Continue without rigid bodies?", "Cancel", "Ok")
                if lRes == 2:
                    createActor("Performer_Actor", False)
    else:
        FBMessageBox("Message", "No optical model found. Import C3D or generate optical model with OWL.", "Ok")


'''---BEGIN SCRIPT---'''
# check namespace
if __name__ in ('__main__', '__builtin__'):

    main()
