find_package(Python3 COMPONENTS Interpreter REQUIRED)
function(rnbo_apply_leak_fix TARGET_FILE)
    message(STATUS "Checking for memory leaks in: ${TARGET_FILE}")
    
    execute_process(
        COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_LIST_DIR}/leak_fixer.py" "${TARGET_FILE}"
        RESULT_VARIABLE RESULT
        OUTPUT_VARIABLE OUTPUT
    )
    
    if(NOT RESULT EQUAL 0)
        message(WARNING "Failed to apply leak fix to ${TARGET_FILE}. Exit code: ${RESULT}")
    else()
        string(STRIP "${OUTPUT}" OUTPUT)
        if(NOT "${OUTPUT}" STREQUAL "")
            message(STATUS "${OUTPUT}")
        endif()
    endif()
endfunction()
macro(rnbo_apply_leak_fix_to_list FILE_LIST)
    foreach(FILE ${FILE_LIST})
        rnbo_apply_leak_fix(${FILE})
    endforeach()
endmacro()
