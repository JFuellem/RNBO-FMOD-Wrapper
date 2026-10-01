cmake_minimum_required(VERSION 3.10.0)

if(APPLE)
    set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64" CACHE STRING "" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS -O3)

get_filename_component(PARENT_DIR ${CMAKE_CURRENT_SOURCE_DIR} DIRECTORY)

# PLUGIN_NAME names the binary; rnboobjname names its C++ factory.
if(PLUGIN_NAME)
    set(_PIPELINE_PLUGIN_NAME "${PLUGIN_NAME}")
endif()

file(READ ${PARENT_DIR}/SrcExportDir/description.json JSON_DESCRIPTION)
string(STRIP "${JSON_DESCRIPTION}" JSON_DESCRIPTION)
string(REGEX MATCH "\"rnboobjname\" *: *\"([^\"]*)\"" RNBO_OBJ_MATCH "${JSON_DESCRIPTION}")
if(CMAKE_MATCH_1)
    set(RNBO_FACTORY_CLASS "${CMAKE_MATCH_1}")
endif()

if(_PIPELINE_PLUGIN_NAME)
    set(PLUGIN_NAME "${_PIPELINE_PLUGIN_NAME}")
elseif(RNBO_FACTORY_CLASS AND NOT RNBO_FACTORY_CLASS STREQUAL "rnbomatic")
    set(PLUGIN_NAME "${RNBO_FACTORY_CLASS}")
else()
    set(PLUGIN_NAME "PlsSetCodeGen")
    message(WARNING "Default rnboobjname 'rnbomatic' detected. Please set a custom class name when exporting from RNBO.")
endif()

if(NOT RNBO_FACTORY_CLASS)
    set(RNBO_FACTORY_CLASS "${PLUGIN_NAME}")
endif()
string(REGEX MATCH "\"rnboversion\" *: *\"([^\"]*)\"" _RNBO_VER_MATCH "${JSON_DESCRIPTION}")
set(RNBO_EXPORT_VERSION "${CMAKE_MATCH_1}")
if(NOT RNBO_EXPORT_VERSION)
    set(RNBO_EXPORT_VERSION "1.4.0")
    message(STATUS "description.json: rnboversion missing; assuming ${RNBO_EXPORT_VERSION} (modern patcher factory)")
endif()
message(STATUS "RNBO export meta.rnboversion: ${RNBO_EXPORT_VERSION}")

# Exports before RNBO 1.4 require PlatformInterface* in the factory signature.
set(_RNBO_LEGACY_FACTORY_DEFAULT OFF)
if(RNBO_EXPORT_VERSION VERSION_LESS "1.4.0")
    set(_RNBO_LEGACY_FACTORY_DEFAULT ON)
endif()
option(RNBO_LEGACY_PATCHER_FACTORY "Pre-1.4 RNBO export: PatcherFactory(PlatformInterface*) + Platform::get (requires matching old RNBO headers in SrcExportDir/rnbo)" ${_RNBO_LEGACY_FACTORY_DEFAULT})
if(RNBO_LEGACY_PATCHER_FACTORY)
    message(STATUS "Patcher factory mode: legacy (export < 1.4.0)")
else()
    message(STATUS "Patcher factory mode: modern (export >= 1.4.0)")
endif()

if(RNBO_LEGACY_PATCHER_FACTORY)
    set(RNBO_FMOD_FACTORY_EXTERN "extern \"C\" RNBO::PatcherFactoryFunctionPtr ${RNBO_FACTORY_CLASS}FactoryFunction(RNBO::PlatformInterface* platformInterface);")
    set(RNBO_FMOD_FACTORY_GETDSP_ALLOC "    RNBO::UniquePtr<RNBO::PatcherInterface> patcherInterfacePtr(${RNBO_FACTORY_CLASS}FactoryFunction(RNBO::Platform::get())());")
else()
    set(RNBO_FMOD_FACTORY_EXTERN "extern \"C\" RNBO::PatcherFactoryFunctionPtr ${RNBO_FACTORY_CLASS}FactoryFunction();")
    set(RNBO_FMOD_FACTORY_GETDSP_ALLOC "    RNBO::UniquePtr<RNBO::PatcherInterface> patcherInterfacePtr(${RNBO_FACTORY_CLASS}FactoryFunction()());")
endif()

set(_RNBO_WRAPPER_DEFS RNBO_NO_PATCHERFACTORY)
if(RNBO_LEGACY_PATCHER_FACTORY)
    list(APPEND _RNBO_WRAPPER_DEFS RNBO_LEGACY_PATCHER_FACTORY=1)
endif()

option(RNBO_UNITY_SOURCE_ONLY "Export Unity sources without a native compiler or platform SDK" OFF)
if(RNBO_UNITY_SOURCE_ONLY)
    project(${PLUGIN_NAME} LANGUAGES NONE)
else()
    project(${PLUGIN_NAME})
endif()
message(STATUS "Building Project: ${PROJECT_NAME} for System: ${CMAKE_SYSTEM_NAME}")

configure_file(../RNBOWrapper/RNBO_FMOD.cpp.in ${CMAKE_BINARY_DIR}/RNBOWrapper/generated/RNBO_FMOD.cpp)
file(GLOB GENERATED_FILES "${CMAKE_BINARY_DIR}/RNBOWrapper/generated/*")

file(GLOB RNBOSRC_FILES "${PARENT_DIR}/SrcExportDir/*.cpp")

option(APPLY_LEAKFIX "Apply memory leak fixes to generated source code (requires Python)" ON)
if(APPLY_LEAKFIX)
    include(${CMAKE_CURRENT_SOURCE_DIR}/LeakFixer.cmake)
    rnbo_apply_leak_fix_to_list("${RNBOSRC_FILES}")
endif()

file(GLOB WRAPPER_HPP_FILES "../RNBOWrapper/RNBOWrapper.hpp")

if(NOT RNBO_UNITY_SOURCE_ONLY)
add_library(oLib OBJECT
    ${RNBOSRC_FILES}
    ${GENERATED_FILES}
)

if(CMAKE_GENERATOR STREQUAL "Xcode")
    target_sources(oLib PRIVATE ${WRAPPER_HPP_FILES})
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
    message(STATUS "Configuring for Emscripten build")

    # Shared runtime prevents duplicate symbols across plugins.
    add_library(rnbo_base STATIC
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.cpp"
        "${PARENT_DIR}/RNBOWrapper/RNBOWrapper.cpp"
    )
    set_target_properties(rnbo_base PROPERTIES ARCHIVE_OUTPUT_DIRECTORY "../BuildProducts")
    target_compile_definitions(rnbo_base PRIVATE ${_RNBO_WRAPPER_DEFS})

    target_include_directories(rnbo_base PRIVATE
        ./inc
        ${PARENT_DIR}/SrcExportDir
        ${PARENT_DIR}/SrcExportDir/rnbo
        ${PARENT_DIR}/SrcExportDir/rnbo/common
        ${PARENT_DIR}/RNBOWrapper
        ${PARENT_DIR}/decoder
    )

    add_library(${PROJECT_NAME} STATIC $<TARGET_OBJECTS:oLib>)
    set_target_properties(${PROJECT_NAME} PROPERTIES ARCHIVE_OUTPUT_DIRECTORY "../BuildProducts")

else()
    message(STATUS "Configuring for non-Emscripten build")
    target_sources(oLib PRIVATE
        "${PARENT_DIR}/SrcExportDir/rnbo/RNBO.cpp"
        "${PARENT_DIR}/RNBOWrapper/RNBOWrapper.cpp"
    )

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

target_include_directories(oLib PRIVATE
    ./inc
    ../SrcExportDir/rnbo
    ../SrcExportDir/rnbo/common
    ../SrcExportDir
    ../RNBOWrapper
    ../decoder
    ${CMAKE_BINARY_DIR}/RNBOWrapper/generated
)

target_compile_definitions(oLib PRIVATE ${_RNBO_WRAPPER_DEFS})
set_target_properties(oLib PROPERTIES POSITION_INDEPENDENT_CODE ON)
endif()

find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    set(_UNITY_BUNDLE_DIR "${PARENT_DIR}/BuildProducts/${PROJECT_NAME}_unity_static")
    set(_UNITY_RUNTIME_DIR "${PARENT_DIR}/BuildProducts/RNBO_FMOD_runtime")
    set(_UNITY_FMOD_DIR "${PARENT_DIR}/BuildProducts/FMOD_unity_inc")
    set(_UNITY_EXPORT_CMD
        ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/unity_static_export.py"
            --out "${_UNITY_BUNDLE_DIR}"
            --runtime-out "${_UNITY_RUNTIME_DIR}"
            --fmod-out "${_UNITY_FMOD_DIR}"
            --plugin-name "${PROJECT_NAME}"
            --generated "${CMAKE_BINARY_DIR}/RNBOWrapper/generated/RNBO_FMOD.cpp"
            --rnbo-src "${PARENT_DIR}/SrcExportDir"
            --wrapper-dir "${PARENT_DIR}/RNBOWrapper"
            --decoder-dir "${PARENT_DIR}/decoder"
            --fmod-inc "${CMAKE_CURRENT_SOURCE_DIR}/inc"
    )
    if(RNBO_LEGACY_PATCHER_FACTORY)
        list(APPEND _UNITY_EXPORT_CMD --legacy-factory)
    endif()
    add_custom_target(unity_static_export
        COMMAND ${_UNITY_EXPORT_CMD}
        COMMENT "Writing Unity FMOD headers, RNBO runtime, and plugin source"
        VERBATIM
    )
else()
    if(RNBO_UNITY_SOURCE_ONLY)
        message(FATAL_ERROR "Python3 is required for unity_static_export")
    endif()
    message(STATUS "Python3 not found: unity_static_export target skipped")
endif()
