# haxe_sublime
Simple Sublime Text plugin for Haxe 4 build and autocompletion

To set hxml file for build target just click on it and open context menu for "Set as current hxml project"

### Settings
 - `haxe_path` : Full path to the Haxe compiler
 - `server_port` (`6110` by default) : Uses [compilation server](http://haxe.org/manual/completion#compilation-cache-server) for autocompletion.
 - `stdin_completion` (`true` by default) : Uses display-stdin completion instead of file saving.