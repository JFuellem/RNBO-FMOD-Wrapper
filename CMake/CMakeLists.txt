
#CMAKE_HOST_SYSTEM_NAME

cmake_minimum_required(VERSION 3.10.0)

project(${PROJECT_NAME})

set(CMAKE_CXX_STANDARD 14)

add_library(${PROJECT_NAME} SHARED ../RNBOExportDir/RNBO.h ../RNBOWrapper/RNBO_FMOD.cpp ../RNBOExportDir/rnbo_source.cpp ../RNBOWrapper/RNBOWrapper.hpp ../RNBOExportDir/RNBO.cpp)

target_include_directories(${PROJECT_NAME} PRIVATE ../../inc)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir/rnbo)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir/common)
target_include_directories(${PROJECT_NAME} PRIVATE ../RNBOExportDir)





