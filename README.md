# RNBO-FMOD-Wrapper

This is an FMOD Wrapper for RNBO, which simplifies the creation of plugins for FMOD.

## RNBO Design instructions
1. Name your Plugin by adding a |param| object with argument ```NAME_<PluginName>```
2. Create an RNBO patch as you like either as an instrument or effect. The presence of in~ and out~ objects determines the type.
3. Add |param| objects that you need. min, max, value and unit attributes will automatically be transferred.
4. Optionally add any or multiple of the following |inports| that will receive 3d-Attributes from the source as a list:

  | Argument | Explanation             |
  |----------|-------------------------|
  | rel_pos  | Relative Position       |
  | rel_vel  | Relative Velocity       |
  | rel_forw | Relative Forward Vector |
  | rel_up   | Relative Up Vector      |
  | abs_pos  | Absolute Position       |
  | abs_vel  | Absolute Velocity       |
  | abs_forw | Absolute Forward Vector |
  | abs_up   | Absolute Up Vector      |

  If the plugin is added to an event as an effect, it automatically turns into a 3D event (even without a spatialiser). For instrument plugins, you must add a spatialiser to preview the effect in FMDO Studio.
  
5. Export it as a C++ Source Code by choosing the RNBOExportDir as Output Directory. No other modifications are needed. Make sure, the export name stays rnbo_source.cpp.

## Build Instructions
1. cd to the CMake folder ```cd CMake```
2. ```cmake -S . -B <SomeFolder> -DPLUGIN_NAME=<PluginName>```
33. ```cmake --build <SomeFolder>```

