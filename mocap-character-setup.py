#***************************************************************************************
# MoCap Character Autosetup for MotionBuilder
#
# REQUIREMENTS: At least 38 optical Markers (C3D or OWL) for only 1 performer.
#               Performer should be in a T-pose facing +Z.
#
# USAGE:
# 1. Open FBX with data in it or import C3D
# 2. Performer should be in a pose at a given frame where all markers are visible to serve as a reference pose
# 3. Execute the script within MotionBuilder
#
# THINGS TO NOTE:
# * The suit must follow the exact same configuration of markers, or the
#   script will not work.
# * Cleanup the marker data beforehand. For joint estimation it is best, that the animation data is non-interrupted.
#
# MISCELLANEOUS:
# * The prefix "FB" in MotionBuilder's types stands for "FilmBox", MotionBuilders former name.
#***************************************************************************************

# Import MotionBuilder libraries
from pyfbsdk import *
from pyfbsdk_additions import *
import os.path
#import math

###############################################################
# Helper Function(s).                                         #
###############################################################

'''---MARKER FUNCTIONS AND VARIABLES---'''
# List of optical markers
markerList = []
# Frame that holds the reference pose, chosen by the user (current frame).
referenceFrame = FBSystem().LocalTime.GetFrame()

# Get position FBVector3d from FBModel m.
def vector(m):
    v = FBVector3d()
    m.GetVector(v)
    return v

# Average positions of a set of FBModels to find the center.
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

# Recursively select markers in scene.
def selectMarkers(root):
    if root:
        for child in root.Children:
            if (child.Name.startswith('M') and child.Name.strip('M').isdigit()) or child.Name.startswith('marker_'):
                child.Selected = True
            selectMarkers(child)

# Collect markers and check count.
def getMarkers():
    global markerList
    # Obtain markers from scene.
    markers = FBModelList()
    selectMarkers(FBSystem().Scene.RootModel)
    FBGetSelectedModels(markers)
    # Reverse marker list, so that M000 is first and so on.
    mCount = markers.GetCount()
    mIndex = mCount - 1
    markerList = []
    for i in range(mCount):
        markerList.append(markers[mIndex - i])
    # Check if enough markers were found.
    suitMarkers = 38
    if len(markers) < suitMarkers:
        FBMessageBox("Message", "Not enough markers found. There should be at least 38 markers attached to the suit", "Ok")
        return False
    else:
        return True


'''---ESTIMATE JOINTS---'''
# In the following skeleton template, the "LeftUpLeg" has "Hips" as its parent,
# marker 29 is used to estimate its position and gets constraint (aim) to it as a driver,
# and its local (x,y,z) default translation is (9.6, -3.6, 7.3) relative to parent.
jointMap = {
    #jointName,     (parentName,    estimators, drivers, constraintType, translation (defaults) )
    'Reference':    (None,          None,       None,       0,  (   0,    0,     0)),
    'Hips':         ('Reference',   [8,9,30,31],[8,9,30,31],0,  (   0, 97.2,  -7.3)),
    'LeftUpLeg':    ('Hips',        [29],       [29],       1,  ( 9.6, -3.6,   7.3)),
    'LeftLeg':      ('LeftUpLeg',   [27,28],    [27,28],    2,  (   0, -42.7, -0.4)),
    'LeftFoot':     ('LeftLeg',     [24,25,26], [24,25,26], 0,  (   0, -43.3, -2.2)),
    'LeftToeBase':  ('LeftFoot',    [25,26],    None,       0,  (   0,  -6.3, 10.9)),
    'RightUpLeg':   ('Hips',        [32],       [32],       1,  (-9.6, -3.6,   7.3)),
    'RightLeg':     ('RightUpLeg',  [33,34],    [33,34],    2,  (   0, -42.7, -0.4)),
    'RightFoot':    ('RightLeg',    [35,36,37], [35,36,37], 0,  (   0, -43.3, -2.2)),
    'RightToeBase': ('RightFoot',   [36,37],    None,       0,  (   0,  -6.3, 10.9)),
    'Spine':        ('Hips',        [6,7],      [4,5,6,7],  2,  (   0,    23,    0)),
    'LeftArm':      ('Spine',       [10,11],    [10,11],    2,  (  12,    18,  0.6)),
    'LeftForeArm':  ('LeftArm',     [12,13],    [12,13],    2,  ( 26.2,   0,  -1.7)),
    'LeftHand':     ('LeftForeArm', [14,15,16], [14,15,16], 0,  ( 26.5,   0,   0.4)),
    'LeftFingerBase':('LeftHand',   [15,16],    None,       0,  (10.55,   0,  1.04)),
    'RightArm':     ('Spine',       [17,18],    [17,18],    2,  (  -12,  18,   0.6)),
    'RightForeArm': ('RightArm',    [19,20],    [19,20],    2,  (-26.2,   0,  -1.7)),
    'RightHand':    ('RightForeArm',[21,22,23], [21,22,23], 0,  (-26.5,   0,   0.4)),
    'RightFingerBase':('RightHand', [22,23],    None,       0,  (-10.55,  0,  1.04)),
    'Neck':         ('Spine',       [6,10,17],  [6,10,17],  2,  (     0,20.5,    0)),
    'Head':         ('Neck',        [0,1,2,3],  [0,1,2,3],  0,  (  0,   15.3,  2.7))
}

# Loading a skeleton template from a config file to generate new jointMap.
def loadJointMap(fileName = None, pPath = None):
    global jointMap
    # If no filename is given, return and use default jointMap.
    if fileName == None:
        return

    if pPath == None:
        print("No path set. Looking into MotionBuilders default config folder.")
        pPath = ""
    else:
        pPath += "\\"
    filePath = pPath + fileName
    if not os.path.isfile(filePath) and pPath != "":
        FBMessageBox("Waring","%s << This file does not exist. Using default settings." % filePath, "Ok")
        return

    # File is created if it does not exist.
    configFile = FBConfigFile(pPath + fileName)

    # Get all the joint names that make up the skeleton.
    jointList = []
    jointIndex = 0
    while True:
        joint = configFile.Get("Joints", "Joint%d" % jointIndex)
        if joint:
            jointIndex += 1
            jointList.append(joint)
        else:
            break

    if len(jointList) == 0:
        FBMessageBox("Warning","No joints found in configuration file. Using defaults.", "Ok")
        return

    # Delete existing content of the jointMap.
    jointMap.clear()

    # Populate the jointMap with joints' config settings.
    for joint in jointList:
        parentJoint = configFile.Get("Joint." + joint, "Parent")

        # Get the markers used for estimation of that joint's position into a list of integers.
        estimators = configFile.Get("Joint." + joint, "Estimators")
        if estimators:
            estimators = [int(m) for m in estimators.split(',') if m.strip()]

        # Get the markers used for driving that joint into a list of integers.
        drivers = configFile.Get("Joint." + joint, "Drivers")
        if drivers:
            drivers = [int(m) for m in drivers.split(',') if m.strip()]

        # Convert string to tuple of floats.
        defaultTranslation = configFile.Get("Joint." + joint, "DefaultTranslation")
        if defaultTranslation:
            defaultTranslation = tuple(float(f) for f in defaultTranslation.split(',') if f.strip())
        # Usually there's no section for the Reference joint, but the defaultTranslation should be at the origin.
        if joint == 'Reference':
            defaultTranslation = (0, 0, 0)

        constraint = 0
        constraintType = configFile.Get("Joint." + joint, "ContraintType")
        if constraintType != None:
            constraint = int(constraintType)

        # Form a key-value-pair that gets inserted into the jointMap.
        dicEntry = {joint: (parentJoint, estimators, drivers, constraint, defaultTranslation)}
        jointMap.update(dicEntry)

# Positions need to be relative to parent joint! Relative translation = child vector - parent vector
# Somehow compute estimation of joint position from its rigid body animation.
def getJointEstimations():
    global markerList, jointMap

    ### Reference joint is a special case, since it has no parent ###
    # We want the Reference joint to be on the floor, centered beneath the hips.

    # Get markers that correspond to jointMap estimators indices.
    estimators = []
    for m in jointMap['Hips'][1]:
        estimators.append(markerList[m])
    if len(estimators) > 0:
        # Find center of hips.
        hips_center = findCenter(estimators)

        # Account for offset between hip marker center and hip pivot location. Prone to change!
        #hips_yoffset = 4.5
        #hips_zoffset = 10.0
        #hips_center[1] -= hips_yoffset
        #hips_center[2] -= hips_zoffset

        # Place the reference joint beneath the hips on the floor.
        referencePos = FBVector3d(hips_center[0],0,hips_center[2])
    else:
        referencePos = FBVector3d(0, 0, 0)
    # Output should be a dictionary with each jointName: estimated position.
    jointEstimations = {'Reference': referencePos}

    '''
    INSERT JOINT ESTIMATION CODE HERE
    '''
    return jointEstimations

# After estimating performer's joint positions from animation, update the jointMap.
def updateJointMapTranslations(jointEstimations):
    global jointMap
    for jointName, (parentName, estimators, drivers, constraintType, translation) in jointMap.iteritems():
        # Only if jointName exists in jointEstimations.
        if parentName != None and jointName in jointEstimations.keys() and parentName in jointEstimations.keys():
            # get relative position to parent and set to jointMap.
            relativeTranslation = jointEstimations[jointName] - jointEstimations[parentName]
            # New tuple with updated translation for jointMap.
            # by unpacking first, because tuples are immutable.
            parentName, estimators, drivers, constraintType, translation = jointMap[jointName]
            jointMap[jointName] = (parentName, estimators, drivers, constraintType, relativeTranslation)
            continue

        # TODO: Don't remember what this was about. Check it out.
        if jointName == 'Reference' and jointName in jointEstimations.keys():
            parentName, estimators, drivers, constraintType, translation = jointMap[jointName]
            jointMap[jointName] = (parentName, estimators, drivers, constraintType, jointEstimations[jointName])

'''---Create Skeleton---'''
# Create a skeleton in a T-pose facing along the positive Z axis.
def createSkeleton(pNamespace):
    global jointMap
    skeleton = {}

    # If there is already pNamespace, show warning and abort
    if FBSystem().Scene.NamespaceExist(pNamespace):
        FBMessageBox("Warning","%s namespace already exists.\nChoose another name for the character." % pNamespace, "Ok")
        return

    # Populate the skeleton with joints.
    for jointName, (parentName, estimators, drivers, constraintType, translation) in jointMap.iteritems():
        if jointName == 'Reference' or jointName == 'Hips':
            # If it is the reference node, create an FBModelRoot.
            joint = FBModelRoot(jointName)

        else:
            # Otherwise, create an FBModelSkeleton.
            joint = FBModelSkeleton(jointName)

        joint.LongName = pNamespace + ':' + joint.Name # Apply the specified namespace to each joint.
        joint.Color = FBColor(0.3, 0.8, 1)             # Cyan
        joint.Size = 250                               # Arbitrary size: big enough to see in viewport.
        joint.Show = True                              # Make the joint visible in the scene.

        # Add the joint to our skeleton.
        skeleton[jointName] = joint

    # Once all the joints have been created, apply the parent/child.
    # relationships to each of the skeleton's joints.
    for jointName, (parentName, estimators, drivers, constraintType, translation) in jointMap.iteritems():
        # Only assign a parent if it exists.
        if parentName != None and parentName in jointMap.keys():
            skeleton[jointName].Parent = skeleton[parentName]

        # The translation should be set after the parent has been assigned.
        skeleton[jointName].Translation = FBVector3d(translation)

    return skeleton

# Characterize the skeleton and create a control rig.
# TODO Check if there's a skeleton in that namespace
def characterizeSkeleton(pCharacterName, pSkeleton, pControlRig = False):
    # If there is no namespace with pCharacterName, show warning and abort
    if not FBSystem().Scene.NamespaceExist(pCharacterName):
        FBMessageBox("Warning","%s namespace does not exists.\nChoose existing skeleton namespace." % pCharacterName, "Ok")
        return

    # Create a new character.
    character = FBCharacter(pCharacterName)
    FBApplication().CurrentCharacter = character

    # Add each joint in our skeleton to the character.
    for jointName, joint in pSkeleton.iteritems():
        slot = character.PropertyList.Find(jointName + 'Link')
        slot.append(joint)

    # Flag that the character has been characterized.
    character.SetCharacterizeOn(True)

    # Create a control rig using Forward and Inverse Kinematics,
    # as specified by the "True" parameter.
    if pControlRig:
        character.CreateControlRig(pControlRig)
        # Set the control rig to active if True.
        character.ActiveInput = pControlRig

    return character

'''---Just for visual style and to prevent error when no mesh is attached to skeleton---'''
# Create a model which will be applied to each joint in the skeleton.
def createModel():
    # Create a sphere.
    model = FBCreateObject('Browsing/Templates/Elements/Primitives', 'Sphere', 'Sphere')
    model.Scaling = FBVector3d(0.5, 0.5, 0.5)

    # Define a slightly reflective dark material.
    material = FBMaterial('SkeletonMaterial')
    material.Ambient = FBColor(0, 0, 0)
    material.Diffuse = FBColor(0, 0.04, 0.08)
    material.Specular = FBColor(0, 0.7, 0.86)
    material.Shininess = 100
    model.Materials.append(material)

    # Create a cartoon-like shader.
    shader = FBCreateObject('Browsing/Templates/Shading Elements/Shaders', 'Edge Cartoon', 'SkeletonShader')

    # For a list of all the shader's properties do:
    #for item in shader.PropertyList:
    #    print item.Name
    aliasProp = shader.PropertyList.Find('Antialiasing')
    aliasProp.Data = True
    colorProp = shader.PropertyList.Find('EdgeColor')
    colorProp.Data = FBColor(0, 0.83, 1)
    widthProp = shader.PropertyList.Find('EdgeWidth')
    widthProp.Data = 8

    # Append the cartoon shader to the model.
    model.Shaders.append(shader)

    # The default shader must also be applied to the model.
    defaultShader = FBSystem().Scene.Shaders[0]
    model.Shaders.append(defaultShader)

    # Use the default shading mode.
    model.ShadingMode = FBModelShadingMode.kFBModelShadingDefault

    return model

# Apply a copy of pModel to each joint in the skeleton.
def applyModelToSkeleton(pSkeleton, pModel):
    # Create a copy of the model for each joint in the skeleton.
    for jointName, joint in pSkeleton.iteritems():
        if jointName == 'Reference':
            # Do not apply the model to the Reference node.
            continue

        # Parent the copied model to the joint.
        model = pModel.Clone()
        model.Parent = joint
        model.Show = True

        # Use the joint name as a prefix.
        model.Name = jointName + pModel.Name

        # Reset the model's translation to place it at the same
        # location as its parent joint.
        model.Translation = FBVector3d(0, 0, 0)

'''---CONNECT MARKERS TO THE SKELETON---'''
# In the end we still need to connect the markers with the skeleton.
# This is done by loading a previously saved mapping from file.
def applyCharacterMapping(pCharacter = FBApplication().CurrentCharacter):
    global markerList
    global jointMap

    if pCharacter == None:
        FBMessageBox("Warning","No character to map markers to!\nCharacterize skeleton first.", "Ok")
        return

    # If we want to save, get the MarkerSet.
    markerSet = pCharacter.GetCharacterMarkerSet(True)

    # Get rid of any existing MarkerSet first and create new one.
    if markerSet:
        markerSet.FBDelete()

    pCharacter.CreateCharacterMarkerSet(True)
    markerSet = pCharacter.GetCharacterMarkerSet(True)

    # Whatever THAT does, but it's in the sample code, so...
    FBBeginChangeAllModels()

    #
    for prop in markerSet.PropertyList:
        if prop.Name.endswith('.Markers'):
            jointName = prop.Name.replace('.Markers', '')
            # Convert marker IDs from driverList to actual marker models in the scene.
            if jointName in jointMap:
                driverList = jointMap[jointName][2]
                # If the joint has no drivers we can't set them up.
                if driverList == None:
                    continue
                markerModelList = []
                for listIndex in range(len(driverList)):
                    driverID = driverList[listIndex]
                    markerModel = markerList[driverID]
                    if markerModel:
                        markerModelList.append(markerModel)

                # Begins a change on multiple plugs.
                prop.BeginChange()
                prop.DisconnectAllSrc()

                for marker in markerModelList:
                    prop.ConnectSrc(marker)

                # Ends a change on multiple plugs.
                prop.EndChange()

                # Get and set the type of constraint for the drivers.
                constraintType = markerSet.PropertyList.Find(prop.Name.replace('.Markers', '.Constraint'))
                if constraintType != None:
                    lType = jointMap[jointName][3]
                    # Expects an integer
                    constraintType.Data = lType

    # Again, I have no idea...
    FBEndChangeAllModels()

###############################################################
# User Interface                                              #
###############################################################
def populateTool(mainLyt):
    # Button callback functions are inside here for scoping, to avoid global variables.
    '''*************************#
    # Button Callback Functions #
    #*************************'''
    def OnCharacterNameChange(control, event):
        OnCharacterNameChange.characterName = control.Text
    # Hack to use outer scope for characterName, because in Python 2.x there's no nonlocal keyword.
    OnCharacterNameChange.characterName = 'MocapSkeleton'

    def loadBtnCallback(control, event):
        # Create the file-open popup and set necessary initial values.
        lFp = FBFilePopup()
        lFp.Caption = "Select a Joint-Map configuration file."
        lFp.Style = FBFilePopupStyle.kFBFilePopupOpen

        # BUG: If we do not set the filter, we will have an exception.
        lFp.Filter = "*"

        # Set the default path.
        lFp.Path = FBSystem().UserConfigPath

        # Get the GUI to show.
        lRes = lFp.Execute()

        # First update the jointMap dictionary, then update the display.
        loadJointMap(lFp.FileName, lFp.Path)
        updateSpreadSheet(spread)

        # Cleanup.
        #del( lFp, lRes, FBFilePopup, FBFilePopupStyle, FBMessageBox )
        del( lFp, lRes)

    def estimateBtnCallback(control, event):
        # If we find enough markers, adjust joint positions.
        if getMarkers():
            jointEstimations = getJointEstimations()
            updateJointMapTranslations(jointEstimations)
            updateSpreadSheet(spread)

    def createBtnCallback(control, event):
        createBtnCallback.skeleton = createSkeleton(OnCharacterNameChange.characterName)
        if createBtnCallback.skeleton:
            # Apply a model to each limb of the skeleton.
            templateModel = createModel()
            applyModelToSkeleton(createBtnCallback.skeleton, templateModel)
            templateModel.FBDelete() # We do not need the template model anymore.
    # Hack to use outer scope for skeleton, because in Python 2.x there's no nonlocal keyword.
    createBtnCallback.skeleton = {}

    def characterizeBtnCallback(control, event):
        # Characterize the skeleton and create a control rig.
        character = characterizeSkeleton(OnCharacterNameChange.characterName, createBtnCallback.skeleton, controlRigRadioBtnCallback.bControlRig)

    def mappingBtnCallback(control, event):
        # Setup the markers as constraints for the joints according to the jointMap drivers
        # Make sure there are markers.
        if getMarkers():
            applyCharacterMapping(FBApplication().CurrentCharacter)

    def automaticBtnCallback(control, event):
        if getMarkers():
            skeleton = createSkeleton(OnCharacterNameChange.characterName)
            # Apply a model to each limb of the skeleton.
            templateModel = createModel()
            applyModelToSkeleton(skeleton, templateModel)
            templateModel.FBDelete() # We do not need the template model anymore.

            # Characterize the skeleton and create a control rig.
            character = characterizeSkeleton(OnCharacterNameChange.characterName, skeleton, False)
            # Setup the markers as constraints for the joints according to the jointMap drivers
            applyCharacterMapping(FBApplication().CurrentCharacter)

    def controlRigRadioBtnCallback(control, event):
        if control.Caption == "Yes":
            controlRigRadioBtnCallback.bControlRig = True
        else:
            controlRigRadioBtnCallback.bControlRig = False
            # Hack to use outer scope for bControlRig, because in Python 2.x there's no nonlocal keyword.
    controlRigRadioBtnCallback.bControlRig = False

    '''*************#
    # Create Layout #
    #*************'''

    # We will use a tabbed layout.
    tab = FBTabControl()

    # Insert tab control
    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(0,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachRight,"")
    h = FBAddRegionParam(0,FBAttachType.kFBAttachBottom,"")

    mainLyt.AddRegion("tab", "tab",x,y,w,h)
    mainLyt.SetControl("tab", tab)

    # Create layouts for the tabs.

    #***************#
    #   Tasks tab   #
    #***************#
    tabName = "Tasks"
    # create a scrollbox
    scrollTasksLyt = FBScrollBox()
    # Content property is the scrollbox's layout: create a region in it
    scrollTasksLyt.Content.AddRegion( "tasksContent", "tasksContent", x, y, w, h )

    # Vertical box layout for the buttons.
    tasksLayout = FBVBoxLayout()

    # set our vertical box layout as the content of the scrollbox
    scrollTasksLyt.Content.SetControl("tasksContent", tasksLayout)
    # init the scrollbox content size. We will be able to scroll on this size.
    scrollTasksLyt.SetContentSize(700, 530)

    # Label and edit box for the name of the skeleton.
    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    lab1 = FBLabel()
    lab1.Caption = "Character Name:"
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.Style = FBTextStyle.kFBTextStyleBold
    lab1.WordWrap = True
    row.Add(lab1, 100)
    editBox = FBEdit()
    editBox.Text = OnCharacterNameChange.characterName
    editBox.OnChange.Add(OnCharacterNameChange)
    row.AddRelative(editBox)
    tasksLayout.Add(row,20)

    # Automatic button
    btn = FBButton()
    btn.Caption = "Automatic"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(automaticBtnCallback)

    # Instruction for manual setup.
    #row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    #row.AddRelative(None)
    lab1 = FBLabel()
    lab1.Caption = "\nManual Setup:"
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.Style = FBTextStyle.kFBTextStyleUnderlined
    lab1.WordWrap = True
    #row.Add(lab1, 100)
    #row.AddRelative(None)
    tasksLayout.Add(lab1,35)

    # Load JointMap button
    btn = FBButton()
    btn.Caption = "1. Load JointMap (optional)"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(loadBtnCallback)

    # Estimate Joint Positions from Markers
    btn = FBButton()
    btn.Caption = "2. Estimate Joint Positions from Markers (optional)"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(estimateBtnCallback)

    # Create Skeleton button
    btn = FBButton()
    btn.Caption = "3. Create Skeleton"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(createBtnCallback)

    # Instruction for manual setup.
    lab1 = FBLabel()
    lab1.Caption = "4. Now manually adjust joint positions if you need to."
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.WordWrap = True
    tasksLayout.Add(lab1,20)

    # Radio Buttons for manual or automatic setup.
    group = FBButtonGroup()
    group.AddCallback(controlRigRadioBtnCallback)

    # First button manual
    rBtnName = "ControlRig"
    rbtn1 = FBButton()
    rbtn1.Caption = "Yes"
    rbtn1.Style = FBButtonStyle.kFBRadioButton
    rbtn1.State = controlRigRadioBtnCallback.bControlRig
    group.Add(rbtn1)

    # Second button automatic
    rBtnName = "NoRig"
    rbtn2 = FBButton()
    rbtn2.Caption = "No"
    rbtn2.Style = FBButtonStyle.kFBRadioButton
    rbtn2.State = not controlRigRadioBtnCallback.bControlRig
    group.Add(rbtn2)

    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    lab1 = FBLabel()
    lab1.Caption = "Generate Control Rig:"
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.WordWrap = True
    row.Add(lab1, 120)
    row.Add(rbtn1, 50)
    row.Add(rbtn2, 50)
    tasksLayout.Add(row,20)

    # Characterize button
    btn = FBButton()
    btn.Caption = "5. Characterize Skeleton"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(characterizeBtnCallback)

    # Character Mapping button
    btn = FBButton()
    btn.Caption = "6. Map Markers onto current character"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasksLayout.Add(btn,60)
    btn.OnClick.Add(mappingBtnCallback)

    tab.Add(tabName,scrollTasksLyt)

    #**************#
    # jointMap tab #
    #**************#
    tabName = "JointMap"
    JMLayout = FBLayout()

    ### Buttons ###
    # TODO: Callback functions for buttons
    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(0,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachRight,"")
    h = FBAddRegionParam(35,FBAttachType.kFBAttachNone,"")
    JMLayout.AddRegion("buttons","buttons", x, y, w, h)

    buttonsLyt = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    btnNames = ["Load", "Save", "SaveAs", "Clear", "Update from Skeleton", "Add Joint", "Remove Joint"]
    for btnName in btnNames:
        b = FBButton()
        b.Caption = btnName
        buttonsLyt.Add(b, 100)
    JMLayout.SetControl("buttons", buttonsLyt)

    ### Spreadsheet ###
    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(40,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachRight,"")
    h = FBAddRegionParam(0,FBAttachType.kFBAttachBottom,"")
    JMLayout.AddRegion("spreadContent","spreadContent", x, y, w, h)

    spread = FBSpread()
    spread.Caption = "Joints"
    JMLayout.SetControl("spreadContent", spread)

    #spread.OnCellChange.Add(OnSpreadEvent)

    updateSpreadSheet(spread)

    tab.Add(tabName,JMLayout)

    #**************#
    #   Help tab   #
    #**************#
    tabName = "Help"

    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(0,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachRight,"")
    h = FBAddRegionParam(0,FBAttachType.kFBAttachBottom,"")

    # create a scrollbox
    scrollHelpLyt = FBScrollBox()
    # Content property is the scrollbox's layout: create a region in it
    scrollHelpLyt.Content.AddRegion( "helpContent", "helpContent", x, y, w, h )

    # For a collapsible layout
    helpLayout = FBLayout()

    # set the collapsible layout as the content of the scrollbox
    scrollHelpLyt.Content.SetControl("helpContent", helpLayout)
    # init the scrollbox content size. We will be able to scroll on this size.
    scrollHelpLyt.SetContentSize(700, 800)

    # The first collapsible help text
    layoutName = "Tasks Help"
    layout = FBLayout()
    x = FBAddRegionParam(10,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(10,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(680,FBAttachType.kFBAttachNone,"")
    h = FBAddRegionParam(400,FBAttachType.kFBAttachNone,"")
    layout.AddRegion(layoutName,layoutName, x, y, w, h)
    layout.SetBorder(layoutName,FBBorderStyle.kFBHighlightBorder,False, True,1,1,90,0)

    arrowName = "BtnArrowTasks"
    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(0,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachNone,"")
    h = FBAddRegionParam(0,FBAttachType.kFBAttachNone,"")
    helpLayout.AddRegion(arrowName ,arrowName , x, y, w, h)

    btn = FBArrowButton()
    helpLayout.SetControl(arrowName ,btn)

    # Important : we set the content AFTER having added the button arrow
    # to its parent layout.
    btn.SetContent( "Help on Tasks", layout, 730, 450 )

    # The second collapsible help text
    #anchor = FBAttachType.kFBAttachBottom
    #anchorRegion = arrowName
    layoutName = "Joint Map Help"
    layout = FBLayout()
    x = FBAddRegionParam(10,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(10,FBAttachType.kFBAttachTop,"")
    w = FBAddRegionParam(680,FBAttachType.kFBAttachNone,"")
    h = FBAddRegionParam(400,FBAttachType.kFBAttachNone,"")
    layout.AddRegion(layoutName,layoutName, x, y, w, h)
    layout.SetBorder(layoutName,FBBorderStyle.kFBHighlightBorder,False, True,1,1,90,0)

    arrowName = "BtnArrowJointMap"
    x = FBAddRegionParam(0,FBAttachType.kFBAttachLeft,"")
    y = FBAddRegionParam(0,FBAttachType.kFBAttachBottom,"BtnArrowTasks")
    w = FBAddRegionParam(0,FBAttachType.kFBAttachNone,"")
    h = FBAddRegionParam(0,FBAttachType.kFBAttachNone,"")
    helpLayout.AddRegion(arrowName ,arrowName , x, y, w, h)

    btn = FBArrowButton()
    helpLayout.SetControl(arrowName ,btn)

    # Important : we set the content AFTER having added the button arrow
    # to its parent layout.
    btn.SetContent( "Help on Joint Map", layout, 730, 450 )

    # Now add the whole help tab to the tab layout
    tab.Add(tabName,scrollHelpLyt)

    # Set starting tab to the first one (Tasks).
    tab.SetContent(0)
    tab.TabPanel.TabStyle = 0 # normal tabs

# Update SpreadSheet
def updateSpreadSheet(spread):
    global jointMap

    # Delete the previous content.
    spread.Clear()

    spread.GetColumn(-1).Width = 100
    spread.ColumnAdd("Parent")
    spread.GetColumn(0).Width = 100
    spread.ColumnAdd("Estimators")
    spread.GetColumn(1).Width = 80
    spread.ColumnAdd("Drivers")
    spread.GetColumn(2).Width = 80
    spread.ColumnAdd("ConstraintType")
    spread.GetColumn(3).Width = 150
    spread.ColumnAdd("rel. X")
    spread.GetColumn(4).Width = 60
    spread.ColumnAdd("rel. Y")
    spread.GetColumn(5).Width = 60
    spread.ColumnAdd("rel. Z")
    spread.GetColumn(6).Width = 60

    # Get data from jointMap
    rowRefIndex = 0
    for jointName in sorted(jointMap.keys()):
        # Add a joint.
        spread.RowAdd(jointName, rowRefIndex)
        # Set the 1st cell of the joint to display parent joint name.
        parentName = str(jointMap[jointName][0])
        spread.SetCellValue(rowRefIndex, 0, parentName)
        # Set the 2nd cell of the joint to show marker IDs for estimation.
        estimators = str(jointMap[jointName][1]).strip('[]')
        spread.SetCellValue(rowRefIndex, 1, estimators)
        # Set the 3rd cell of the joint to show marker IDs for constraints.
        drivers = str(jointMap[jointName][2]).strip('[]')
        spread.SetCellValue(rowRefIndex, 2, drivers)
        # Show the type of constraint in the 4th cell.
        #TODO Radiobutton for 3 options
        spread.GetSpreadCell(rowRefIndex,3).Style = FBCellStyle.kFBCellStyleInteger
        spread.SetCellValue(rowRefIndex, 3, jointMap[jointName][3])
        # Split the translation into 3 seperate columns (5th, 6th, 7th).
        spread.GetSpreadCell(rowRefIndex,4).Style = FBCellStyle.kFBCellStyleDouble
        spread.SetCellValue(rowRefIndex, 4, jointMap[jointName][4][0])
        spread.GetSpreadCell(rowRefIndex,5).Style = FBCellStyle.kFBCellStyleDouble
        spread.SetCellValue(rowRefIndex, 5, jointMap[jointName][4][1])
        spread.GetSpreadCell(rowRefIndex,6).Style = FBCellStyle.kFBCellStyleDouble
        spread.SetCellValue(rowRefIndex, 6, jointMap[jointName][4][2])

        rowRefIndex += 1


def createTool():
    # Tool creation will serve as the hub for all other controls.
    tool = FBCreateUniqueTool("Motion Capture Skeleton Setup")
    tool.StartSizeX = 762
    tool.StartSizeY = 610
    populateTool(tool)
    ShowTool(tool)

###############################################################
# Main.                                                       #
###############################################################
def main():
    createTool()

# This is actually where the script starts.
# check namespace
if __name__ in ('__main__', '__builtin__'):

    main()
