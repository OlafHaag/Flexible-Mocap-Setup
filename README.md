# Mocap Character Setup

## *Python Script for Motionbuilder*

This is my first attempt to write a python script for Motionbuilder, so it's up for optimization.

### About

Its main purpose is to generate a skeleton that fits into recorded marker data by estimating the joints' positions. Ideally it should be able to deliver a one-click solution for setting up a character that fits into recorded marker data and which can then be used in subsequent live sessions with the same performer.

The motivation behind it is, that current available workflows of setting up a character for a virtual reality live session demand a high level of expertise, don't work well and simply are too time consuming.

Furthermore, the script should avoid pitfalls of other proprietary solutions, that lack control over the process and outcome. That's why the script will enable:

* custom humanoid skeletons (by setting up a "Joint Map")
* adjusting joints after they're created
* assign markers as 'drivers' (constraints) to joints (via "Joint Map" by using MoBu's flexible mocap workflow)

What it will **not** provide any time soon and isn't planned:

* spectral clustering of markers to form rigid bodies (that's still done "manually" via Joint Map; we have a few active markers in our setup, so there's no need for overkill)
* generate arbitrary skeletons from data (we always use the same mocap suit, no animals, so we don't need that either)

But your're always welcome to fork the project and work on such things yourself.

We are working on eliminating the necessity for a reference frame, the T-pose. But we will see about that. MotionBuilder might still need that for the characterization.

### Usage

Just drag script into the MotionBuilder view and execute. A user interface will open.
More help will will be available once the main parts are done.

*This script is part of a research project at the Philipps-University Marburg.*
