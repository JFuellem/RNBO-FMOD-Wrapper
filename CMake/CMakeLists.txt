
#CMAKE_HOST_SYSTEM_NAME

cmake_minimum_required(VERSION 3.10.0)

if(APPLE)
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)
endif()

project(${PLUGIN_NAME})

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_FLAGS -Ofast)

add_library(${PROJECT_NAME} SHARED ../RNBOExportDir/rnbo/RNBO.h ../RNBOWrapper/RNBO_FMOD.cpp ../RNBOExportDir/rnbo_source.cpp ../RNBOWrapper/RNBOWrapper.hpp ../RNBOExportDir/rnbo/RNBO.cpp)

if(APPLE)
 set_target_properties(${PROJECT_NAME} PROPERTIES LIBRARY_OUTPUT_DIRECTORY ../BuildProducts)
else()
 set_target_properties(${PROJECT_NAME} PROPERTIES RUNTIME_OUTPUT_DIRECTORY ../BuildProducts)
endif()

target_include_directories(${PROJECT_NAME} PRIVATE ./inc)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir/rnbo)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir/rnbo/common)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir)





