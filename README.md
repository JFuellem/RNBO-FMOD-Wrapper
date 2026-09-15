# RNBO-FMOD-Wrapper

This is an FMOD Wrapper for RNBO, which simplifies the creation of plugins for FMOD.

## RNBO Design instructions

1. Create an RNBO patch as you like either as an instrument or effect. The presence of in~ and out~ objects determines the type.
**2a. Featuring Multichannel-Expansion:** All effects with one in~ and one out~ channel are expanded to the channel configuration inside the middleware.
2. Add |param| objects that you need. min, max, value and unit attributes will automatically be transferred.
3. Optionally add any or multiple of the following |inports| that will receive 3d-Attributes from the source as a list:

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
  
4. Go to the Export as a C++ Source Code and set a classname, which determines the plugins name. Clone the repo and choose SrcExportDir as output directory. No other modifications are needed.

## Build Instructions

1. Clone Repo if not already done.
2. Firelight technologies doesn't want the redistribution of their headers, so please download the FMOD Engine API and copy the FMOD api/core/inc folder into the CMake folder so that the structure is repo/CMake/inc. 
3. cd to the CMake folder ```cd /path/to/CMake```
4. ```cmake -B Build```
5. ```cmake --build Build```
6. Find your plugins in the BuildProducts folder.

## Unity static source (IL2CPP)

Export C++ sources for Unity to compile into IL2CPP players. Requires Python and the FMOD headers from the build instructions above.

```bash
cd /path/to/CMake
cmake -B BuildSource -DRNBO_UNITY_SOURCE_ONLY=ON
cmake --build BuildSource --target unity_static_export
```

Copy these folders into `Assets/Plugins/RNBO_FMOD/`:

- `BuildProducts/FMOD_unity_inc/` — once
- `BuildProducts/RNBO_FMOD_runtime/` — once, using the same RNBO version as all plugins
- `BuildProducts/<PluginName>_unity_static/` — per plugin

In FMOD Settings, add `<PluginName>_GetDSPDescription` to **Static Plugins** for the target platform. Keep the compiled dynamic plugin for the Editor.

## Things to consider
Feel free to try out the additional GUI Compiler [here](https://github.com/JFuellem/RNBO-FMOD-Compiler).

The performance of these plugins is worse than the ones FMOD provides. You can test the performance with the profiler.

If you find any bugs or something isn't working as expected, feel free to add a bug report or contact me.

If you're feeling generous, you can donate [here](https://www.paypal.com/donate/?business=5WX6KRT4HFEU2&no_recurring=1&currency_code=CHF).
