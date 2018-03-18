# ***************************************************************************************
# Flexible MoCap Character Setup for MotionBuilder
# GOALS:
#   - Easy setup.
#   - Create skeleton from estimated joint positions.
#   - Be able to make changes to the skeleton.
#   - Animate the skeleton by real-time optical marker stream.
#
# REQUIREMENTS:
#   *.c3d - recording of marker data.
#   *.csv - template topology for skeleton and marker-to-joint mappings.
#   *_offsets.csv - estimated offsets for joints and markers for specific performer-/session.
#   optional:
#   *.txt - marker labels that match those in the skeleton template.
#   *.rbs - rigid body marker preset that matches the C3D file for stabilizing occluded markers.
#   *.xml - skeleton definition for character definition if your skeleton doesn't follow HIK naming conventions.
#   *.bvh - generated animation from the c3d file (with skeleton estimation scripts). Can serve as ground truth.
#
# USAGE:
#   1. Import the C3D and optionally the corresponding BVH file (ground truth) into MotionBuilder.
#   2. Execute the script within MotionBuilder and follow the steps
#
# MISCELLANEOUS Info:
# * The prefix "FB" in MotionBuilder's types stands for "FilmBox", MotionBuilders former name.
# ***************************************************************************************
import os.path
import csv

# Import MotionBuilder libraries
from pyfbsdk import *
from pyfbsdk_additions import *

# FixMe: for development. Disable when executed in MoBu!
#from pyfbsdk_gen_doc import *


# ---HELPER FUNCTIONS---
class Nonlocals(object):
    """ Helper class to implement nonlocal names in Python 2.x """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        
        
def is_empty(any_structure):
    """
    Check if any object evaluates as being empty, e.g. empty list.
    :param any_structure: Any object which can be interpreted as being emtpy.
    :return: Is the structure empty or not?
    :rtype: bool
    """
    if any_structure:
        return False
    else:
        return True


def deselect_all():
    """Deselects each component in the scene.
    """
    for comp in FBSystem().Scene.Components:
        comp.Selected = False
      
      
# ---MARKER FUNCTIONS---
def get_optical_markers(root=None, marker_list=None):
    """
    Recursively find models of subtype FBModelMarkerOptical in the scene.
    :param root: Parent, is not returned
    :param marker_list: Used in recursion. List to add markers to. If None is given, it'll be created.
    :type marker_list: list
    :return: List of optical markers in scene.
    :rtype: list
    """
    if marker_list is None:
        marker_list = list()
    if not root:
        root = FBSystem().Scene.RootModel
    for child in root.Children:
        if child.FbxGetObjectSubType() == 'FBModelMarkerOptical':
            marker_list.append(child)
        get_optical_markers(child, marker_list)
    return marker_list
    

def check_optical_markers(marker_names, marker_namespace):
    """
    Checks if FBModelMarkerOptical models by names in marker_names are in the scene.
    Pops up an error message if markers weren't found.
    :param marker_names: The names of the markers that should be in the scene.
    :type marker_names: list
    :param marker_namespace: In which Namespace the markers are located.
    :type marker_namespace: str
    :return: Do the names check out or not?
    :rtype: bool
    """
    fails = list()
    for name in marker_names:
        model = FBFindModelByLabelName(":".join([marker_namespace, name]) if marker_namespace else name)
        if not model or model.FbxGetObjectSubType() != 'FBModelMarkerOptical':
            fails.append(name)
    if not is_empty(fails):
        FBMessageBox("Error", "Marker(s) {} couldn't be found.".format(",".join(fails)), "Ok")
        return False
    else:
        return True


def read_marker_labels(filename):
    """
    Reads a text file and puts each line into a list.
    :param filename: full file path to the text file.
    :type filename: str
    :return: List with marker labels.
    :rtype: list
    """
    marker_labels = list()
    try:
        with open(filename, 'r') as f:
            marker_labels = f.read().splitlines()
            # Get rid of any quotation marks.
            marker_labels[:] = [s.strip('\"') for s in marker_labels]
    except IOError:
        FBMessageBox("Error", "Could not read from file\n{}\nMake sure that the file exists.".format(filename), "OK")
    return marker_labels


def rename_markers(new_labels):
    """
    Gets markers from scene and renames them to the labels provided. Numbers must match.
    :param new_labels: List of new names for the markers.
    :type new_labels: list
    """
    markers = get_optical_markers()
    if len(markers) != len(new_labels):
        FBMessageBox("Error", "Number of labels must match number of markers.", "OK")
    else:
        for i, marker in enumerate(markers):
            marker.Name = new_labels[i]
            
    
def move_markers(position_map):
    """
    Takes the markers in the scene and if they appear in the position map, they will be moved.
    :param position_map: Dictionary of marker label to position.
    :type position_map: dict
    """
    markers = get_optical_markers()
    for marker in markers:
        if marker.Name in position_map:
            position = FBVector3d(position_map[marker.Name])
            marker.Translation = position
    
    
# ---SKELETON FUNCTIONS---
def read_template_file(fullpath):
    """
    Read skeleton data from CSV file.
    :param fullpath: full file path to the CSV file.
    :type fullpath: str
    :return: List of dictionaries with information on joint's name, parent, offsets, type, rotation_mode.
    :rtype: list
    """
    skeleton_info = list()
    try:
        with open(fullpath) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # We don't read all keys. Only those that are necessary for now.
                entry = {'name': row['name'],
                         'parent': row['parent'],
                         'offset_x': row['offset_x'],
                         'offset_y': row['offset_y'],
                         'offset_z': row['offset_z'],
                         'type': row['type'],
                         'rotation_mode': row['rotation_mode']}
                skeleton_info.append(entry)
    except IOError:
        FBMessageBox("Error", "Could not read from file\n{}\nMake sure that the file exists.".format(fullpath), "OK")
    finally:
        return skeleton_info


def write_template(fullpath, content):
    """
    Save data as CSV file.
    :param fullpath: full file path to where the CSV file should be saved.
    :type fullpath: str
    :param content: List containing information for each joint with name, parent, offsets, bounds, type, rotation_mode.
    :type content: list
    """
    try:
        with open(fullpath, 'wb') as csvFile:
            fieldnames = ['name', 'parent', 'offset_x', 'offset_y', 'offset_z',
                          'bound_x_min', 'bound_x_max', 'bound_y_min', 'bound_y_max', 'bound_z_min', 'bound_z_max',
                          'type', 'rotation_mode', 'optimize_group']
            csvWriter = csv.DictWriter(csvFile, fieldnames=fieldnames)
            csvWriter.writeheader()
            for item in content:
                csvWriter.writerow(item)
    except IOError:
        FBMessageBox("Error",
                     "Could not write to file\n{}\nMake sure you have permission\nto write to folder.".format(fullpath),
                     "Ok")


def create_skeleton(namespace, joint_list, create_marker_dummies=False):
    """
    Create a joint_map in a T-pose facing along the positive Z axis.
    :param namespace: namespace to precede the joint names.
    :type namespace: str
    :param joint_list: joint data
    :type joint_list: list
    :param create_marker_dummies: Whether to create dummy joints for the estimated marker positions or not.
    :type create_marker_dummies: bool
    :return: List of FBModelSkeleton nodes.
    :rtype: list
    """

    # If there is already a Namespace of that name, show warning and abort.
    if FBSystem().Scene.NamespaceExist(namespace):
        FBMessageBox("Warning",
                     "{} namespace already exists.\nChange or delete the namespace\n"
                     "before creating a new skeleton.".format(namespace),
                     "Ok")
        return None
    
    # If there's no joint_list, show warning and abort
    if is_empty(joint_list):
        FBMessageBox("Warning", "No skeleton definition.", "Ok")
        return None
    
    joint_map = {}  # A dictionary of joint name to FBModelSkeleton node mappings.
    # Populate the joint_map with joints.
    for joint_info in joint_list:
        name = joint_info['name']
        joint_type = joint_info['type']
        if not joint_info['parent']:
            # If it is the root node, create an FBModelRoot.
            joint = FBModelRoot(name)
        else:
            # Otherwise, create an FBModelSkeleton.
            if not create_marker_dummies and joint_type == 'marker':
                continue
            joint = FBModelSkeleton(name)  # FixMe: Add Namespace from the beginning, otherwise a number is appended and characterization doesn't work.
        
        joint.LongName = namespace + ':' + joint.Name  # Apply the specified namespace to each joint.
        joint.Size = 100  # Arbitrary size: big enough to see in viewport.
        joint.Show = True  # Make the joint visible in the scene.
        if joint_type == 'marker':  # Differentiate markers from joints.
            joint.Color = FBColor(1.0, 0.0, 0)
        else:
            joint.Color = FBColor(0.3, 0.8, 1)
        
        # Add the joint to our joint_map.
        joint_map[name] = joint
    
    # Once all the joints have been created, apply the parent/child relationships to each of the joint_map's joints.
    for joint_info in joint_list:
        if not create_marker_dummies and joint_info['type'] == 'marker':
            continue

        name = joint_info['name']
        # Only assign a parent if it exists.
        parent_name = joint_info['parent']
        if parent_name in joint_map:
            joint_map[name].Parent = joint_map[parent_name]
        
        # The translation should be set after the parent has been assigned.
        try:
            translation = (float(joint_info['offset_x']) * 100.0,
                           float(joint_info['offset_y']) * 100.0,
                           float(joint_info['offset_z']) * 100.0)  # Convert to cm.
        except ValueError:  # e.g. root joints that don't have an offset.
            translation = (0.0, 0.0, 0.0)
        
        joint_map[name].Translation = FBVector3d(translation)
        # Rotation/Scaling pivot offsets are placed where offset would be globally, must be 0.
        prop_rot_pivot = joint_map[name].PropertyList.Find('Rotation Pivot')
        prop_rot_pivot.Data = FBVector3d(0, 0, 0)
        prop_scale_pivot = joint_map[name].PropertyList.Find('Scaling Pivot')
        prop_scale_pivot.Data = FBVector3d(0, 0, 0)
    return list(joint_map.itervalues())
        

def get_skeleton_data():
    """
    Get information on selected joint and its children as dictionaries in a list.
    :return: list of selected joint and its children.
    :rtype: list
    """
    selected_models = FBModelList()
    FBGetSelectedModels(selected_models)
    if len(selected_models) != 1:
        FBMessageBox("Warning", "Please only select the root joint.", "Ok")
        return None
    joint_list = get_joints_info(selected_models[0])
    return joint_list


def get_joint_list(node=None, joint_list=None):
    """
    Get all the joints in selected hierarchy.
    :return: A list of FBModelSkeleton nodes.
    :rtype: list
    """
    if is_empty(joint_list):
        joint_list = list()
        
    if node is None:
        selected_models = FBModelList()
        FBGetSelectedModels(selected_models)
        if len(selected_models) == 0:
            FBMessageBox("Warning", "Please select at least one joint.", "Ok")
            return None
        else:
            for node in selected_models:
                get_joint_list(node, joint_list)
    else:
        joint_list.append(node)
        for child in node.Children:
            get_joint_list(child, joint_list)
    joint_list = list(set(joint_list))  # Remove possible duplicates.
    return joint_list
    
    
def zero_joint_rotation(node=None):
    """Sets rotation of selected joint and child-nodes to 0,0,0.
    """
    if node is None:
        selected_models = FBModelList()
        FBGetSelectedModels(selected_models)
        if len(selected_models) == 0:
            FBMessageBox("Warning", "Please select at least one joint.", "Ok")
            return None
        else:
            for node in selected_models:
                zero_joint_rotation(node)
    else:
        node.Rotation = FBVector3d(0.0, 0.0, 0.0)
        for child in node.Children:
            zero_joint_rotation(child)


def get_bounds(offset):
    """
    Returns a dictionary with min/max bounds for x,y,z around the offset-vector.
    :param offset: Vector describing 3D coordinates.
    :type offset: FBVector3d
    :return: bounds in meter as dictionary.
    :rtype: dict
    """
    bounds = dict()
    for i, val in enumerate(offset):
        axis = chr(120 + i)  # x, y, or z
        bounds['bound_{}_min'.format(axis)] = (offset[i] - 20.0) / 100.0
        bounds['bound_{}_max'.format(axis)] = (offset[i] + 20.0) / 100.0
    return bounds


def get_joints_info(node, joint_list=None):
    """
    Recurse through the skeleton from given node downwards and collect information on the joints.
    Save this information as dictionaries in a list.
    :param node: starting node of the topology.
    :type node: FBModelSkeleton
    :param joint_list: Used in recursion. List to add joints to. If None is given, it'll be created.
    :return: List of dictionaries with information on joints.
    :rtype: list
    """
    if is_empty(joint_list):
        joint_list = list()
    # We only want skeleton nodes.
    node_type = node.FbxGetObjectSubType()
    if node_type == 'FBModelRoot' or node_type == 'FBModelSkeleton':
        entry = {'name': node.Name}
        try:
            entry['parent'] = node.Parent.Name
        except AttributeError:  # root has no parent.
            pass
        try:
            if node.Color == FBColor(1.0, 0.0, 0.0):
                entry['type'] = 'marker'
                entry['rotation_mode'] = ''
            else:
                entry['type'] = 'bone'
                if node.RotationActive:
                    entry['rotation_mode'] = 'hinge'  # Todo: or 'twist', by checking limits? Check limits to determine if hingeX, hingeY, or hingeZ.
                else:
                    entry['rotation_mode'] = 'ball'
        except AttributeError:  # FBModelRoot has no Attribute Color
            pass
        if node.Parent:
            node_translation = FBVector3d()
            node.GetVector(node_translation)
            parent_translation = FBVector3d()
            node.Parent.GetVector(parent_translation)
            offset = node_translation - parent_translation
            entry['offset_x'] = offset[0] / 100.0
            entry['offset_y'] = offset[1] / 100.0
            entry['offset_z'] = offset[2] / 100.0
        else:  # Must be root.
            entry['parent'] = ''
            entry['type'] = 'bone'
            offset = None
            entry['offset_x'] = ''
            entry['offset_y'] = ''
            entry['offset_z'] = ''
            entry['rotation_mode'] = ''
        
        if len(node.Children) == 0 and entry['type'] == 'bone':
            entry['type'] = 'end'
            entry['rotation_mode'] = ''
        else:
            if not is_empty(offset):
                entry.update(get_bounds(offset))
        
        joint_list.append(entry)
        for child in node.Children:
            get_joints_info(child, joint_list)
        return joint_list
        

def get_estimated_offsets(fullfilepath):
    """
    Load joint estimations from csv file.
    :param fullfilepath: full path to csv file
    :type fullfilepath: str
    :return: Dictionary containing offsets for joint labels.
    :rtype: dict
    """
    estimations = dict()
    try:
        with open(fullfilepath, 'rb') as filehandle:
            reader = csv.reader(filehandle)
            for row in reader:
                offset = [float(o) for o in row[1:]]
                estimations.update({row[0]: FBVector3d(offset)})
    except IOError:
        FBMessageBox("Error", "Estimation file {}\n could not be read.".format(os.path.basename(fullfilepath)), "OK")
        return None
    except ImportError as e:
        FBMessageBox("Error", "Wrong file format\n{}".format(e.message), "OK")
    return estimations


def characterize_skeleton(char_name, joints, create_control_rig=False):
    """
    Characterize the skeleton and create a control rig if necessary.
    :param char_name: Name of the character.
    :type char_name: str
    :param joints: List of FBModelSkeleton nodes.
    :type joints: list
    :param create_control_rig: Whether to create a control rig.
    :type create_control_rig: bool
    :return: character
    :rtype: FBCharacter
    """
    # Create a new character.
    character = FBCharacter(char_name)
    FBApplication().CurrentCharacter = character
    
    # Add each joint in our list to the character.
    fails = list()
    for joint in joints:
        slot = character.PropertyList.Find(joint.Name + 'Link')  # todo: This only works for HIK naming convention. Prompt for preset?
        if slot is not None:
            slot.append(joint)
        else:
            fails.append(joint.Name)
    if not is_empty(fails):
        print "While characterization, no slots were found for {}.".format(",".join(fails))
    
    # Flag that the character has been characterized.
    character.SetCharacterizeOn(True)
    
    if create_control_rig:
        # Create a control rig using Forward and Inverse Kinematics
        character.CreateControlRig(create_control_rig)
        # Set the control rig to active.
        character.ActiveInput = create_control_rig
    
    return character


# Just for visual style and to prevent error when no mesh is attached to skeleton
def create_visualization_primitive(geometry='Sphere'):
    """
    Create a model which will be applied to each joint in the skeleton.
    :param geometry: Which form of primitive model should be created.
    :type geometry: str
    :return: model
    """
    # Create a sphere.
    model = FBCreateObject('Browsing/Templates/Elements/Primitives', geometry, geometry)
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
    # for item in shader.PropertyList:
    #    print(item.Name)
    alias_prop = shader.PropertyList.Find('Antialiasing')
    alias_prop.Data = True
    color_prop = shader.PropertyList.Find('EdgeColor')
    color_prop.Data = FBColor(0, 0.83, 1)
    width_prop = shader.PropertyList.Find('EdgeWidth')
    width_prop.Data = 8
    
    # Append the cartoon shader to the model.
    model.Shaders.append(shader)
    
    # The default shader must also be applied to the model.
    default_shader = FBSystem().Scene.Shaders[0]
    model.Shaders.append(default_shader)
    
    # Use the default shading mode.
    model.ShadingMode = FBModelShadingMode.kFBModelShadingDefault
    
    return model


def apply_model_to_skeleton(skeleton_node, model):
    """
    Apply a copy of model to each joint in the skeleton.
    :param skeleton_node: Reference to root skeleton node in the scene.
    :param model: Reference to the model that should be applied.
    """
    # Do not apply the model to the Reference node.
    if skeleton_node.Name.lower() == 'reference':
        return
    # Do not apply model to leaves.
    if len(skeleton_node.Children) == 0:
        return
    else:
        # Parent the copied model to the joint.
        new_model = model.Clone()
        new_model.Parent = skeleton_node
        new_model.Show = True
        
        # Use the joint name as a prefix.
        new_model.Name = skeleton_node.Name + "_" + model.Name
        new_model.ProcessObjectNamespace(FBNamespaceAction.kFBConcatNamespace, skeleton_node.OwnerNamespace.Name)
        
        # Reset the model's translation to place it at the same
        # location as its parent joint.
        new_model.Translation = FBVector3d(0, 0, 0)  # ToDo: Copy rotation in case model is not a sphere? Scale model to bone length.
        # Recurse through the topology.
        for child in skeleton_node.Children:
            apply_model_to_skeleton(child, model)


def map_markers_to_character(joint_list, marker_namespace, character=None):
    """
    Connect the markers to the skeleton with flexible mocap workflow.
    :param joint_list: List with information for each joint's name, parent, offset_x/y/z, type, rotation_mode
    :type joint_list: list
    :param character: Character whose joints shall be constrained to markers.
    :return: Whether the mapping was successful or not.
    :rtype: bool
    """
    if character is None:
        character = FBApplication().CurrentCharacter
    # If there's still no character, abort.
    if character is None:
        FBMessageBox("Warning", "No character to map markers to!\nCharacterize skeleton first.", "Ok")
        return False
    
    # Get rid of any existing MarkerSet first and create new one.
    marker_set = character.GetCharacterMarkerSet(True)
    if marker_set:
        marker_set.FBDelete()
    character.CreateCharacterMarkerSet(True)
    marker_set = character.GetCharacterMarkerSet(True)
    
    # Whatever THAT does, but it's in the sample code, so...
    FBBeginChangeAllModels()
    
    # Fill the markerset properties.
    for prop in marker_set.PropertyList:
        if prop.Name.endswith('.Markers'):
            joint_name = prop.Name.replace('.Markers', '')
            # Todo: Doesn't this require joints to follow HIK naming convention? Need Mapping?
            # Entries that have this joint as parent and are of type marker.
            marker_names = [m['name'] for m in joint_list if m['parent'] == joint_name and m['type'] == 'marker']
            # If the joint has no markers as children, or if there's no such joint in the list, we can't map to it.
            if is_empty(marker_names):
                continue
            # Find the matching marker models in the scene.
            marker_models = list()
            for marker_name in marker_names:
                marker = FBFindModelByLabelName(':'.join([marker_namespace, marker_name]) if marker_namespace else marker_name)
                if marker:
                    marker_models.append(marker)
            num_markers = len(marker_models)
            
            # Begins a change on multiple plugs.
            prop.BeginChange()
            prop.DisconnectAllSrc()
            # Connect the marker models to the joint.
            for marker in marker_models:
                prop.ConnectSrc(marker)
            
            # Ends a change on multiple plugs.
            prop.EndChange()
            
            # Set the type of goal for the joint.
            constraint_type = marker_set.PropertyList.Find(prop.Name.replace('.Markers', '.Constraint'))
            if constraint_type is not None and num_markers > 0:
                # Make the goal type dependent on the number of markers.
                if num_markers == 1:
                    goal_type = 1  # Aim joint at markers.
                elif num_markers == 2:
                    goal_type = 2  # Rotate joint in markers.
                elif num_markers >= 3:
                    goal_type = 0  # Position and rotate joint in markers.
                # Expects an integer
                constraint_type.Data = goal_type
    
    # Again, I have no idea...
    FBEndChangeAllModels()
    return True


###############################################################
# User Interface                                              #
###############################################################
def populate_tool(main_layout):
    """
    Sets up the GUI elements of the tool
    :param main_layout: The FBTool
    """
    # Button callback functions are inside here for scoping, to avoid global variables.
    '''*************************#
    # Button Callback Functions #
    #*************************'''
    nl = Nonlocals(character_name="MocapSkeleton",
                   template_path=None,
                   skeleton_data=None,
                   joint_nodes=list(),
                   namespace='Mocap',
                   namespaces=FBList(),
                   marker_namespace='',
                   create_markers=True,
                   control_rig=False)
    
    spread = FBSpread()
    spread.Caption = "Joints"
    
    def on_character_name_change(control, event):
        nl.character_name = control.Text
    
    def on_namespace_change(control, event):
        nl.namespace = control.Text
    
    def on_marker_namespace_change(control, event):
        nl.marker_namespace = control.Items[control.ItemIndex]
    
    nl.namespaces.OnChange.Add(on_marker_namespace_change)
    nl.namespaces.Style = FBListStyle.kFBDropDownList
    
    def update_namespaces_list():
        nl.namespaces.Items.removeAll()
        for name_space in FBSystem().Scene.Namespaces:
            nl.namespaces.Items.append(name_space.Name)
        nl.namespaces.Items.append('')  # Add empty namespace in case markers don't have any.
        
        nl.namespaces.Selected(0, True)
        for i, name_space in enumerate(nl.namespaces.Items):
            # We assume C3D is the default namespace for optical markers.
            if name_space.lower() == 'c3d':
                nl.marker_namespace = name_space
                nl.namespaces.Selected(i, True)
                break
            elif name_space.lower() == 'owl':
                nl.marker_namespace = name_space
                nl.namespaces.Selected(i, True)
    
    update_namespaces_list()
    
    def on_update_list_btn(control, event):
        update_namespaces_list()
        
    # TODO: Make automatic setup functional.
    def automatic_btn_callback(control, event):
        """
        These are all the setup steps in one sweep instead of manual setup, a one-click solution.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # Template:
        # Load template and estimations
        # Create skeleton
        # Characterize
        # Map markers

        # BVH:
        # Remember Frame (all markers visible)
        # zero rotation
        # Read skeleton topology
        # Characterize
        # Evaluate frame/set to remembered frame
        # Map markers
        pass
    
    def load_btn_callback(control, event):
        """
        Load skeleton data from template file.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # Create the file-open popup and set necessary initial values.
        lFp = FBFilePopup()
        lFp.Caption = "Select a skeleton template file."
        lFp.Style = FBFilePopupStyle.kFBFilePopupOpen
        
        # BUG: If we do not set the filter, we will have an exception.
        lFp.Filter = "*.csv"
        
        # Set the default path.
        if not nl.template_path:
            lFp.Path = FBSystem().UserConfigPath
        else:
            lFp.Path = os.path.dirname(nl.template_path)
        
        # Get the GUI to show.
        lRes = lFp.Execute()
        if lRes:
            # Remember path for quick saving.
            nl.template_path = lFp.FullFilename
            # First update the joint_map dictionary, then update the display.
            nl.skeleton_data = read_template_file(lFp.FullFilename)
            update_spreadsheet(spread, nl.skeleton_data)
        
        # Cleanup.
        del (lFp, lRes)
    
    def load_offsets_btn_callback(control, event):
        """
        Prompts file dialog and reads offsets to apply to skeleton data.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # Create the file-open popup and set necessary initial values.
        lFp = FBFilePopup()
        lFp.Caption = "Select a CSV file with offsets."
        lFp.Style = FBFilePopupStyle.kFBFilePopupOpen

        # BUG: If we do not set the filter, we will have an exception.
        lFp.Filter = "*.csv"

        # Set the default path.
        if not nl.template_path:
            lFp.Path = FBSystem().UserConfigPath
        else:
            lFp.Path = os.path.dirname(nl.template_path)

        # Get the GUI to show.
        lRes = lFp.Execute()
        if lRes:
            # First update the joint_map dictionary.
            offset_map = get_estimated_offsets(lFp.FullFilename)
            if not is_empty(offset_map):
                for joint_info in nl.skeleton_data:
                    joint_name = joint_info['name']
                    if joint_name in offset_map.iterkeys():
                        # Since these are mutable data types, we work directly on them and nl.skeleton_data gets updated.
                        joint_info['offset_x'] = offset_map[joint_name][0]
                        joint_info['offset_y'] = offset_map[joint_name][1]
                        joint_info['offset_z'] = offset_map[joint_name][2]
                # Now update the display.
                update_spreadsheet(spread, nl.skeleton_data)

        # Cleanup.
        del (lFp, lRes)
    
    def create_btn_callback(control, event):
        """
        Creates a new skeleton.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        nl.joint_nodes = create_skeleton(nl.namespace, nl.skeleton_data, nl.create_markers)
        update_namespaces_list()
        
    def create_geometry_btn_callback(control, event):
        """
        Attaches meshes to nl.joint_nodes.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        if nl.joint_nodes:
            # Find root of skeleton.
            for j in nl.joint_nodes:
                if j.Parent is None:
                    root = j
                    break
            # Apply a model to each limb of the skeleton.
            templateModel = create_visualization_primitive()
            apply_model_to_skeleton(root, templateModel)
            templateModel.FBDelete()  # We do not need the template model anymore.
    
    def create_markers_radio_btn_callback(control, event):
        if control.Caption == "Yes":
            nl.create_markers = True
        else:
            nl.create_markers = False
        
    def zero_rotation_btn_callback(control, event):
        """
        Sets rotation of selected joint and child-nodes to 0,0,0.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        zero_joint_rotation()
    
    def characterize_btn_callback(control, event):
        """
        Characterize the skeleton and create a control rig.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        character = characterize_skeleton(nl.character_name, nl.joint_nodes, nl.control_rig)
    
    def rename_markers_btn_callback(control, event):
        """
        Prompts for a text file with labels and renames markers in scene.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # Create the file-open popup and set necessary initial values.
        lFp = FBFilePopup()
        lFp.Caption = "Select a text file with labels."
        lFp.Style = FBFilePopupStyle.kFBFilePopupOpen

        # BUG: If we do not set the filter, we will have an exception.
        lFp.Filter = "*.txt"

        # Set the default path.
        if not nl.template_path:
            lFp.Path = FBSystem().UserConfigPath
        else:
            lFp.Path = os.path.dirname(nl.template_path)
        lRes = lFp.Execute()
        if lRes:
            new_names = read_marker_labels(lFp.FullFilename)
            rename_markers(new_names)
        
    def move_markers_btn_callback(control, event):
        """
        Move optical markers to dummy joints that match name.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        positions = dict()
        joint_map = {j.Name: j for j in nl.joint_nodes}
        for info in nl.skeleton_data:
            # Search for joint in nl.skeleton_data to determine if it is a marker dummy.
            if info['type'] == 'marker':
                dummy_name = info['name']
                if dummy_name in joint_map:
                    global_vector = FBVector3d()
                    joint_map[dummy_name].GetVector(global_vector)
                    positions.update({dummy_name: global_vector})
        move_markers(positions)
        
    def mapping_btn_callback(control, event):
        """
        Setup the markers as constraints for the joints.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        if nl.skeleton_data:
            marker_names = [info['name'] for info in nl.skeleton_data if info['type'] == 'marker']
        else:
            FBMessageBox("Error", "No skeleton data available for mapping.", "Ok")
            return
        
        # Make sure there are markers.
        if check_optical_markers(marker_names, nl.marker_namespace):
            map_markers_to_character(nl.skeleton_data, nl.marker_namespace, FBApplication().CurrentCharacter)
            
    def control_rig_radio_btn_callback(control, event):
        if control.Caption == "Yes":
            nl.control_rig = True
        else:
            nl.control_rig = False
            
    def save_btn_callback(control, event):
        """
        Overwrite existing template file with skeleton data. Call SaveAs if file does not exist.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # If file does not exist, return and use default joint_map.
        if not os.path.isfile(nl.template_path):
            saveAs_btn_callback(control, event)
        else:
            write_template(nl.template_path, nl.skeleton_data)
    
    def saveAs_btn_callback(control, event):
        """
        Save skeleton data to template file.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        # Create the file-save popup and set necessary initial values.
        lFp = FBFilePopup()
        lFp.Caption = "Save skeleton template file."
        lFp.Style = FBFilePopupStyle.kFBFilePopupSave
        
        # BUG: If we do not set a filter, we will have an exception.
        lFp.Filter = "*.csv"

        # Set the default path.
        if not nl.template_path:
            lFp.Path = FBSystem().UserConfigPath
        else:
            lFp.Path = os.path.dirname(nl.template_path)
        
        # Get the GUI to show.
        lRes = lFp.Execute()
        
        if lRes:
            # If no filename is given, return and display an error warning.
            if lFp.FileName is None:
                FBMessageBox("Warning", "No file name was given. Aborted.", "Ok")
                return
            
            # Save path for later use with Save button.
            nl.template_path = lFp.FullFilename
            write_template(nl.template_path, nl.skeleton_data)
        
        # Cleanup.
        del (lFp, lRes)
    
    def clear_btn_callback(control, event):
        """
        Clear the skeleton data and initialize the spreadsheet's columns
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        nl.skeleton_data = list()
        spreadInit(spread)
    
    def update_from_skeleton_btn_callback(control, event):
        """
        Update skeleton data from selected skeleton.
        :param control: Widget in which event occurred.
        :param event: Which event occurred.
        """
        nl.skeleton_data = get_skeleton_data()
        nl.joint_nodes = get_joint_list()
        update_spreadsheet(spread, nl.skeleton_data)
    
    '''*************#
    # Create Layout #
    #*************'''
    # We will use a tabbed layout.
    tab = FBTabControl()
    
    # Insert tab control
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
    h = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")
    
    main_layout.AddRegion("tab", "tab", x, y, w, h)
    main_layout.SetControl("tab", tab)
    
    # Create layouts for the tabs.
    
    # ***************#
    #   Tasks tab    #
    # ***************#
    tab_name = "Tasks"
    # create a scrollbox
    scroll_tasks_layout = FBScrollBox()
    # Content property is the scrollbox's layout: create a region in it
    scroll_tasks_layout.Content.AddRegion("tasksContent", "tasksContent", x, y, w, h)
    
    # Vertical box layout for the buttons.
    tasks_layout = FBVBoxLayout()
    
    # set our vertical box layout as the content of the scrollbox
    scroll_tasks_layout.Content.SetControl("tasksContent", tasks_layout)
    # init the scrollbox content size. We will be able to scroll on this size.
    scroll_tasks_layout.SetContentSize(700, 680)
    
    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    lab1 = FBLabel()
    lab1.Caption = "Namespace:"
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.Style = FBTextStyle.kFBTextStyleBold
    lab1.WordWrap = True
    row.Add(lab1, 80)
    edit_box = FBEdit()
    edit_box.Text = nl.namespace
    edit_box.OnChange.Add(on_namespace_change)
    row.Add(edit_box, 100)
    
    # Label and edit box for the name of the skeleton.
    lab1 = FBLabel()
    lab1.Caption = "Character Name:"
    lab1.Justify = FBTextJustify.kFBTextJustifyLeft
    lab1.Style = FBTextStyle.kFBTextStyleBold
    lab1.WordWrap = True
    row.Add(lab1, 120)
    edit_box = FBEdit()
    edit_box.Text = nl.character_name
    edit_box.OnChange.Add(on_character_name_change)
    row.AddRelative(edit_box)
    tasks_layout.Add(row, 20)
    
    # Automatic button
    btn = FBButton()
    btn.Caption = "Automatic"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(automatic_btn_callback)
    tasks_layout.Add(btn, 60)
    
    # Instruction for manual setup.
    lable_manual = FBLabel()
    lable_manual.Caption = "\nManual Setup:"
    lable_manual.Justify = FBTextJustify.kFBTextJustifyLeft
    lable_manual.Style = FBTextStyle.kFBTextStyleUnderlined
    lable_manual.WordWrap = True
    tasks_layout.Add(lable_manual, 35)
    
    # Load template button
    btn = FBButton()
    btn.Caption = "Load Template"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(load_btn_callback)
    tasks_layout.Add(btn, 60)
    
    # Load estimated offsets button
    btn = FBButton()
    btn.Caption = "Load estimated joint offsets (optional)"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(load_offsets_btn_callback)
    tasks_layout.Add(btn, 60)
    
    # Create Skeleton button
    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    btn = FBButton()
    btn.Caption = "Create Skeleton"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(create_btn_callback)
    row.Add(btn, 200)

    create_markers_lbl = FBLabel()
    create_markers_lbl.Caption = "Create Dummy Markers:"
    create_markers_lbl.Justify = FBTextJustify.kFBTextJustifyLeft
    create_markers_lbl.WordWrap = True
    row.Add(create_markers_lbl, 80)

    # Radio Buttons for Yes/No to ControlRig.
    group = FBButtonGroup()
    group.AddCallback(create_markers_radio_btn_callback)

    # First button: Yes
    rbtn1 = FBButton()
    rbtn1.Caption = "Yes"
    rbtn1.Style = FBButtonStyle.kFBRadioButton
    rbtn1.State = nl.create_markers
    group.Add(rbtn1)

    # Second button: No
    rbtn2 = FBButton()
    rbtn2.Caption = "No"
    rbtn2.Style = FBButtonStyle.kFBRadioButton
    rbtn2.State = not nl.create_markers
    group.Add(rbtn2)

    row.Add(rbtn1, 50)
    row.Add(rbtn2, 50)
    tasks_layout.Add(row, 60)
    
    # Instruction for adjusting joints.
    labInstruction = FBLabel()
    labInstruction.Caption = "Now manually adjust joint positions if you need to."
    labInstruction.Justify = FBTextJustify.kFBTextJustifyLeft
    labInstruction.WordWrap = True
    tasks_layout.Add(labInstruction, 20)

    # Attach Meshes button
    btn = FBButton()
    btn.Caption = "Attach Meshes to joints (optional)"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    tasks_layout.Add(btn, 60)
    btn.OnClick.Add(create_geometry_btn_callback)
    
    # Put these into 1 row, because they belong together.
    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    # Zero rotation button
    btn = FBButton()
    btn.Caption = "Base Pose/Zero Rotation"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(zero_rotation_btn_callback)
    row.Add(btn, 200)
    
    # Characterize button
    btn = FBButton()
    btn.Caption = "Characterize HIK Skeleton"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(characterize_btn_callback)
    row.Add(btn, 200)
    
    control_rig_lbl = FBLabel()
    control_rig_lbl.Caption = "\nGenerate\nControl Rig:"
    control_rig_lbl.Justify = FBTextJustify.kFBTextJustifyLeft
    control_rig_lbl.WordWrap = True
    row.Add(control_rig_lbl, 80)
    
    # Radio Buttons for Yes/No to ControlRig.
    group = FBButtonGroup()
    group.AddCallback(control_rig_radio_btn_callback)
    
    # First button: Yes
    rbtn1 = FBButton()
    rbtn1.Caption = "Yes"
    rbtn1.Style = FBButtonStyle.kFBRadioButton
    rbtn1.State = nl.control_rig
    group.Add(rbtn1)
    
    # Second button: No
    rbtn2 = FBButton()
    rbtn2.Caption = "No"
    rbtn2.Style = FBButtonStyle.kFBRadioButton
    rbtn2.State = not nl.control_rig
    group.Add(rbtn2)
    
    row.Add(rbtn1, 50)
    row.Add(rbtn2, 50)
    tasks_layout.Add(row, 60)
    
    # Marker manipulation buttons
    btn = FBButton()
    btn.Caption = "Rename Markers"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(rename_markers_btn_callback)
    tasks_layout.Add(btn, 60)
    
    btn = FBButton()
    btn.Caption = "Move Markers to Dummies"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(move_markers_btn_callback)
    tasks_layout.Add(btn, 60)
    
    # Character Mapping button
    row = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    btn = FBButton()
    btn.Caption = "Map Markers onto current character"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(mapping_btn_callback)
    row.Add(btn, 250)
    
    marker_namespace_lbl = FBLabel()
    marker_namespace_lbl.Caption = "Marker Namespace:"
    marker_namespace_lbl.Justify = FBTextJustify.kFBTextJustifyLeft
    marker_namespace_lbl.Style = FBTextStyle.kFBTextStyleBold
    row.Add(marker_namespace_lbl, 130)
    row.Add(nl.namespaces, 200)
    
    # Update namespaces button
    btn = FBButton()
    btn.Caption = "Update List"
    btn.Justify = FBTextJustify.kFBTextJustifyLeft
    btn.OnClick.Add(on_update_list_btn)
    row.AddRelative(btn)
    tasks_layout.Add(row, 60)
    
    tab.Add(tab_name, scroll_tasks_layout)
    
    # **************#
    # joint_map tab #
    # **************#
    tab_name = "JointMap"
    skeleton_data_layout = FBLayout()
    
    ### Buttons ###
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
    h = FBAddRegionParam(35, FBAttachType.kFBAttachNone, "")
    skeleton_data_layout.AddRegion("buttons", "buttons", x, y, w, h)
    
    buttons_layout = FBHBoxLayout(FBAttachType.kFBAttachLeft)
    
    # Load JointMap button
    btn = FBButton()
    btn.Caption = "Load Template"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(load_btn_callback)
    buttons_layout.Add(btn, 120)

    # Load offsets button
    btn = FBButton()
    btn.Caption = "Load Estimations"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(load_offsets_btn_callback)
    buttons_layout.Add(btn, 120)
    
    # Save JointMap button
    btn = FBButton()
    btn.Caption = "Save"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(save_btn_callback)
    buttons_layout.Add(btn, 60)
    
    # SaveAs JointMap button
    btn = FBButton()
    btn.Caption = "SaveAs"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(saveAs_btn_callback)
    buttons_layout.Add(btn, 60)
    
    # Clear JointMap button
    btn = FBButton()
    btn.Caption = "Clear"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(clear_btn_callback)
    buttons_layout.Add(btn, 60)
    
    # update from skeleton JointMap button
    btn = FBButton()
    btn.Caption = "Update from Skeleton"
    btn.Justify = FBTextJustify.kFBTextJustifyCenter
    btn.OnClick.Add(update_from_skeleton_btn_callback)
    buttons_layout.Add(btn, 140)
    
    skeleton_data_layout.SetControl("buttons", buttons_layout)
    
    ### Spreadsheet ###
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(40, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
    h = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")
    skeleton_data_layout.AddRegion("spreadContent", "spreadContent", x, y, w, h)
    
    skeleton_data_layout.SetControl("spreadContent", spread)
    
    # TODO If the values of the translations are changed, after a skeleton has been created, move joints accordingly.
    # spread.OnCellChange.Add(OnSpreadEvent)
    
    tab.Add(tab_name, skeleton_data_layout)
    
    # **************#
    #   Help tab   #
    # **************#
    tab_name = "Help"
    
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachRight, "")
    h = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "")
    
    # create a scrollbox
    scrollHelpLyt = FBScrollBox()
    # Content property is the scrollbox's layout: create a region in it
    scrollHelpLyt.Content.AddRegion("helpContent", "helpContent", x, y, w, h)
    
    # For a collapsible layout
    helpLayout = FBLayout()
    
    # set the collapsible layout as the content of the scrollbox
    scrollHelpLyt.Content.SetControl("helpContent", helpLayout)
    # init the scrollbox content size. We will be able to scroll on this size.
    scrollHelpLyt.SetContentSize(700, 800)
    
    # The first collapsible help text
    layoutName = "Tasks Help"
    layout = FBLayout()
    x = FBAddRegionParam(10, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(10, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(680, FBAttachType.kFBAttachNone, "")
    h = FBAddRegionParam(400, FBAttachType.kFBAttachNone, "")
    layout.AddRegion(layoutName, layoutName, x, y, w, h)
    layout.SetBorder(layoutName, FBBorderStyle.kFBHighlightBorder, False, True, 1, 1, 90, 0)
    
    arrowName = "BtnArrowTasks"
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(0, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachNone, "")
    h = FBAddRegionParam(0, FBAttachType.kFBAttachNone, "")
    helpLayout.AddRegion(arrowName, arrowName, x, y, w, h)
    
    btn = FBArrowButton()
    helpLayout.SetControl(arrowName, btn)
    
    # Important : we set the content AFTER having added the button arrow
    # to its parent layout.
    btn.SetContent("Help on Tasks", layout, 730, 450)
    
    # The second collapsible help text
    # anchor = FBAttachType.kFBAttachBottom
    # anchorRegion = arrowName
    layoutName = "Joint Map Help"
    layout = FBLayout()
    x = FBAddRegionParam(10, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(10, FBAttachType.kFBAttachTop, "")
    w = FBAddRegionParam(680, FBAttachType.kFBAttachNone, "")
    h = FBAddRegionParam(400, FBAttachType.kFBAttachNone, "")
    layout.AddRegion(layoutName, layoutName, x, y, w, h)
    layout.SetBorder(layoutName, FBBorderStyle.kFBHighlightBorder, False, True, 1, 1, 90, 0)
    
    arrowName = "BtnArrowJointMap"
    x = FBAddRegionParam(0, FBAttachType.kFBAttachLeft, "")
    y = FBAddRegionParam(0, FBAttachType.kFBAttachBottom, "BtnArrowTasks")
    w = FBAddRegionParam(0, FBAttachType.kFBAttachNone, "")
    h = FBAddRegionParam(0, FBAttachType.kFBAttachNone, "")
    helpLayout.AddRegion(arrowName, arrowName, x, y, w, h)
    
    btn = FBArrowButton()
    helpLayout.SetControl(arrowName, btn)
    
    # Important : we set the content AFTER having added the button arrow
    # to its parent layout.
    btn.SetContent("Help on Joint Map", layout, 730, 450)
    
    # Now add the whole help tab to the tab layout
    tab.Add(tab_name, scrollHelpLyt)
    
    # Set starting tab to the first one (Tasks).
    tab.SetContent(0)
    tab.TabPanel.TabStyle = 0  # normal tabs


def spreadInit(spread):
    """
    Deletes spreadsheet content and resets columns.
    :param spread: spread sheet instance.
    """
    # Delete the previous content.
    spread.Clear()
    
    spread.GetColumn(-1).Width = 100
    spread.ColumnAdd("Parent")
    spread.GetColumn(0).Width = 100
    spread.ColumnAdd("Type")
    spread.GetColumn(1).Width = 80
    spread.ColumnAdd("Rotation Mode")
    spread.GetColumn(2).Width = 80
    spread.ColumnAdd("rel. X")
    spread.GetColumn(3).Width = 60
    spread.ColumnAdd("rel. Y")
    spread.GetColumn(4).Width = 60
    spread.ColumnAdd("rel. Z")
    spread.GetColumn(5).Width = 60
    #spread.ColumnAdd("ConstraintType")
    #spread.GetColumn(6).Width = 150


def update_spreadsheet(spread, joint_list):
    """
    Resets the spreadsheet and fills the cells with data from joint_list.
    :param spread: spreadsheet instance.
    :param joint_list: List of dictionaries with information on joint's name, parent, offsets, type, rotation_mode.
    :type joint_list: list
    """
    spreadInit(spread)
    
    rowRefIndex = 0
    for joint_info in joint_list:
        # Add a joint.
        spread.RowAdd(joint_info['name'], rowRefIndex)
        # Set cell values.
        spread.SetCellValue(rowRefIndex, 0, joint_info['parent'])
        spread.SetCellValue(rowRefIndex, 1, joint_info['type'])
        spread.SetCellValue(rowRefIndex, 2, joint_info['rotation_mode'])
        spread.GetSpreadCell(rowRefIndex, 3).Style = FBCellStyle.kFBCellStyleDouble
        # Convert offsets to floats. Check if offset is not empty.
        spread.SetCellValue(rowRefIndex, 3, float(joint_info['offset_x']) if joint_info['offset_x'] else '')
        spread.GetSpreadCell(rowRefIndex, 4).Style = FBCellStyle.kFBCellStyleDouble
        spread.SetCellValue(rowRefIndex, 4, float(joint_info['offset_y']) if joint_info['offset_y'] else '')
        spread.GetSpreadCell(rowRefIndex, 5).Style = FBCellStyle.kFBCellStyleDouble
        spread.SetCellValue(rowRefIndex, 5, float(joint_info['offset_z']) if joint_info['offset_z'] else '')
        # todo: Show the type of constraint in one cell.
        # todo Radiobutton for 3 options for contraint?
        
        rowRefIndex += 1


def createTool():
    """
    Tool creation will serve as the hub for all other controls.
    """
    tool = FBCreateUniqueTool("Flexible Motion Capture Skeleton Setup")
    tool.StartSizeX = 768
    tool.StartSizeY = 768
    populate_tool(tool)
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
