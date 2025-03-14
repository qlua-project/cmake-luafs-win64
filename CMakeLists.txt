cmake_minimum_required ( VERSION 3.30 )
project ( luafs VERSION 1.8.0
                LANGUAGES C )

set ( LFS_DIR "src" CACHE PATH "Source Directory of 'lunarmodules/luafilesystem' module" )
set ( ENV{LUA_DIR} "externals/lua" )
if ( CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT )
  set_property ( CACHE CMAKE_INSTALL_PREFIX PROPERTY VALUE ${PROJECT_SOURCE_DIR} )
endif ()

message( STATUS "CMAKE_BUILD_TYPE ${CMAKE_BUILD_TYPE}")
message( STATUS "CMAKE_INSTALL_PREFIX ${CMAKE_INSTALL_PREFIX}")
message( STATUS "LUA_DIR $ENV{LUA_DIR}")
message( STATUS "LFS_DIR ${LFS_DIR}")

find_package( Lua REQUIRED )
message( STATUS "Lua Version ${LUA_VERSION_STRING}")
message( STATUS "Lua Includes ${LUA_INCLUDE_DIR}")
message( STATUS "Lua Library ${LUA_LIBRARY}")
message( STATUS "Lua Libraries ${LUA_LIBRARIES}")

set ( LFS_SRC src/lfs.c )
set ( LFS_DEF src/lfs.def )

list( TRANSFORM LFS_SRC PREPEND "${LFS_DIR}/" )
list( TRANSFORM LFS_DEF PREPEND "${LFS_DIR}/" )

add_library ( lfs MODULE ${LFS_SRC} )
target_include_directories ( lfs PRIVATE ${LUA_INCLUDE_DIR} )
target_link_options ( lfs PRIVATE ${CMAKE_LINK_DEF_FILE_FLAG}${PROJECT_SOURCE_DIR}/${LFS_DEF} )
target_link_libraries ( lfs ${LUA_LIBRARIES} )
set_target_properties ( lfs PROPERTIES OUTPUT_NAME "lfs" )

install ( TARGETS lfs LIBRARY DESTINATION "bin" )
