# Flexible Mocap Setup

## *Python Script for Motionbuilder*

### About

Its main purpose is to quickly create a skeleton which joints' positions were fitted into recorded marker data *beforehand*.

The motivation behind it is, that current available workflows of setting up a character for a virtual reality live session demand a high level of expertise, don't work well and simply are too time consuming.

Furthermore, the script should avoid pitfalls of other proprietary solutions, that lack control over the process and outcome. That's why the script should enable:

* Easy setup.
* Create custom skeletons (by setting up a »Skeleton Template«)
* Apply estimated joint positions to the template.
* Be able to make changes to the skeleton after creation.
* Animate the skeleton by real-time optical marker stream by using MotionBuilder's flexible mocap workflow.

What it will **not** provide any time soon and isn't planned:

* Spectral clustering of markers to form rigid bodies automatically.
* Estimating the joint positions from the marker data. We use other scripts for that and unfortunately, due to patenting reasons, I cannot share the code.

But your're always welcome to fork the project and work on such things yourself.

### REQUIREMENTS:
* *.c3d - recording of marker data.
* *.csv - template topology for skeleton and marker-to-joint mappings.
* *_offsets.csv - estimated offsets for joints and markers for specific performer-/session.

optional:
* *.txt - marker labels that match those in the skeleton template.
* *.rbs - rigid body marker preset that matches the C3D file for stabilizing occluded markers.
* *.xml - skeleton definition for character definition if your skeleton doesn't follow HIK naming conventions.
* *.bvh - generated animation from the c3d file (with skeleton estimation scripts). Can serve as ground truth.

### USAGE:
1. Import the C3D and optionally the corresponding BVH file (ground truth) into MotionBuilder.
2. Execute the script within MotionBuilder and follow the steps
