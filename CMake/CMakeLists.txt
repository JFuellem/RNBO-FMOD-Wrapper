
#CMAKE_HOST_SYSTEM_NAME

cmake_minimum_required(VERSION 3.10.0)

if(APPLE)
set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS -Ofast)

get_filename_component(PARENT_DIR ${CMAKE_CURRENT_SOURCE_DIR} DIRECTORY)

file(GLOB WRAPPER_FILES "${PARENT_DIR}/RNBOWrapper/*")
file(GLOB RNBOSRC_FILES
    "${PARENT_DIR}/SrcExportDir/*.cpp"
    "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.h"
    "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.cpp"
)

file(READ ${PARENT_DIR}/SrcExportDir/description.json JSON_DESCRIPTION)
string(STRIP "${JSON_DESCRIPTION}" JSON_DESCRIPTION)
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

configure_file(../RNBOWrapper/RNBO_FMOD.cpp.in ${CMAKE_BINARY_DIR}/RNBOWrapper/generated/RNBO_FMOD.cpp)

file(GLOB GENERATED_FILES "${CMAKE_BINARY_DIR}/RNBOWrapper/generated/*")




project(${PLUGIN_NAME})

#make library for potential multiple targets
add_library(oLib OBJECT ${RNBOSRC_FILES} ${WRAPPER_FILES} ${GENERATED_FILES})
set_target_properties(oLib PROPERTIES POSITION_INDEPENDENT_CODE ON)

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

target_include_directories(oLib PRIVATE ./inc)
target_include_directories(oLib PRIVATE ../SrcExportDir/rnbo)
target_include_directories(oLib PRIVATE ../SrcExportDir/rnbo/common)
target_include_directories(oLib PRIVATE ../SrcExportDir)
target_include_directories(oLib PRIVATE ../RNBOWrapper)
target_include_directories(oLib PRIVATE ${CMAKE_BINARY_DIR}/RNBOWrapper/generated)





