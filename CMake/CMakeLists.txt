#CMAKE_HOST_SYSTEM_NAME

cmake_minimum_required(VERSION 3.10.0)

# Basic compiler settings
if(APPLE)
    set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS -O3)

# Get parent directory and files
get_filename_component(PARENT_DIR ${CMAKE_CURRENT_SOURCE_DIR} DIRECTORY)


file(GLOB WRAPPER_FILES "${PARENT_DIR}/RNBOWrapper/*")
file(GLOB RNBO_COMMON_FILES "${PARENT_DIR}/SrcExportDir/rnbo/common/*")

# Determine plugin name
file(READ ${PARENT_DIR}/SrcExportDir/description.json JSON_DESCRIPTION)
string(STRIP "${JSON_DESCRIPTION}" JSON_DESCRIPTION)

# First try to get rnboobjname directly
string(REGEX MATCH "\"rnboobjname\" *: *\"([^\"]*)\"" RNBO_OBJ_MATCH "${JSON_DESCRIPTION}")
if(CMAKE_MATCH_1)
    set(PLUGIN_NAME "${CMAKE_MATCH_1}")
    message(STATUS "Found rnboobjname: ${PLUGIN_NAME}")
else()
    # Fall back to existing name detection logic
    string(REGEX MATCH "\"meta\" *: *\\{[^\\}]*\"name\" *: *\"([^\"]*)\"" MATCHES "${JSON_DESCRIPTION}")

    if("${CMAKE_MATCH_1}" STREQUAL "untitled")
        message(STATUS "Standard Rnbo name detected: ${CMAKE_MATCH_1}, searching further...")
        string(REGEX MATCH "\"meta\" *: *\\{[^\\}]*\"rnboobjname\" *: *\"([^\"]*)\"" MATCHES "${JSON_DESCRIPTION}")
    endif()

    if("${CMAKE_MATCH_1}" STREQUAL "rnbomatic")
        message(STATUS "Standard Rnbo object name detected: ${CMAKE_MATCH_1}, searching further...")
        string(REGEX MATCH "\"Name_([^\"]+)\"" MATCHES "${JSON_DESCRIPTION}")
    endif()

    if("${CMAKE_MATCH_1}" STREQUAL "")
        set(PLUGIN_NAME "Untitled")
        message(STATUS "No name found, defaulting to: ${PLUGIN_NAME}")
    else()
        set(PLUGIN_NAME "${CMAKE_MATCH_1}")
        message(STATUS "Name found: ${CMAKE_MATCH_1}")
    endif()
endif()

# Set project name after determining plugin name
project(${PLUGIN_NAME})
message(STATUS "Detected CMAKE_SYSTEM_NAME: ${CMAKE_SYSTEM_NAME}")

# For Emscripten builds, create separate base library
if(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
    message(STATUS "Configuring rnbo_base target")
    # Create base RNBO library
    add_library(rnbo_base STATIC
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.cpp"
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.h"
    )
    
    # Setup include directories for base library
    target_include_directories(rnbo_base PRIVATE
        ${PARENT_DIR}/SrcExportDir
        ${PARENT_DIR}/SrcExportDir/rnbo
        ${PARENT_DIR}/SrcExportDir/rnbo/common
    )
    
    set_target_properties(rnbo_base PROPERTIES 
        ARCHIVE_OUTPUT_DIRECTORY "../BuildProducts"
    )
    
    # Plugin-specific files (excluding RNBO.cpp)
    file(GLOB RNBOSRC_FILES
        "${PARENT_DIR}/SrcExportDir/*.cpp"
    )
else()
    file(GLOB RNBOSRC_FILES
        "${PARENT_DIR}/SrcExportDir/*.cpp"
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.h"
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.cpp"
    )
endif()

# Template files
configure_file(../RNBOWrapper/RNBO_FMOD.cpp.in ${CMAKE_BINARY_DIR}/RNBOWrapper/generated/RNBO_FMOD.cpp)
configure_file(../RNBOWrapper/RNBOWrapper.cpp.in ${CMAKE_BINARY_DIR}/RNBOWrapper/generated/RNBOWrapper.cpp)

file(GLOB GENERATED_FILES "${CMAKE_BINARY_DIR}/RNBOWrapper/generated/*")

# Library setup
add_library(oLib OBJECT ${RNBOSRC_FILES} ${WRAPPER_FILES} ${GENERATED_FILES})
set_target_properties(oLib PROPERTIES POSITION_INDEPENDENT_CODE ON)

if(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
    add_library(${PROJECT_NAME} STATIC $<TARGET_OBJECTS:oLib>)
    set_target_properties(${PROJECT_NAME} PROPERTIES 
        ARCHIVE_OUTPUT_DIRECTORY "../BuildProducts"
    )
else()
    # For other platforms, create shared libraries
    add_library(${PROJECT_NAME} SHARED $<TARGET_OBJECTS:oLib>)
    
    if(APPLE)
        add_library(${PROJECT_NAME}_bundle MODULE $<TARGET_OBJECTS:oLib>)
        set_target_properties(${PROJECT_NAME}_bundle PROPERTIES
            BUNDLE TRUE
            OUTPUT_NAME "${PROJECT_NAME}"
            LIBRARY_OUTPUT_DIRECTORY "../BuildProducts"
        )
    endif()

    if(APPLE OR UNIX)
        set_target_properties(${PROJECT_NAME} PROPERTIES LIBRARY_OUTPUT_DIRECTORY ../BuildProducts)
    else()
        set_target_properties(${PROJECT_NAME} PROPERTIES RUNTIME_OUTPUT_DIRECTORY ../BuildProducts)
    endif()
endif()

# Include directories
target_include_directories(oLib PRIVATE ./inc)
target_include_directories(oLib PRIVATE ../SrcExportDir/rnbo)
target_include_directories(oLib PRIVATE ../SrcExportDir/rnbo/common)
target_include_directories(oLib PRIVATE ../SrcExportDir)
target_include_directories(oLib PRIVATE ../RNBOWrapper)
target_include_directories(oLib PRIVATE ${CMAKE_BINARY_DIR}/RNBOWrapper/generated)

target_compile_definitions(oLib PRIVATE RNBO_NO_PATCHERFACTORY)





