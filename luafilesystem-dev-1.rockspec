package = "luafilesystem"
version = "dev-1"
source = {
   url = "https://github.com/qlua-project/cmake-luafs-win64",
   tag = "1.8.0",
}
supported_platforms = {
    "win32",
}
dependencies = {
   "lua >= 5.1"
}
build = {
   type = "builtin",
   platforms = {
      windows = {
         install = {
            lib = {
               "bin/lfs.dll",
            }
         },
         modules = {},
      },
   },
}