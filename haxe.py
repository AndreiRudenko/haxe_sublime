import sys, os, subprocess, shutil, shlex, json, codecs, time
import sublime, sublime_plugin
import mdpopups

from .haxe_parse_completion_list import haxe_completion_list, haxe_has_error, haxe_has_args

#plugin location
plugin_file = __file__
plugin_filepath = os.path.realpath(plugin_file)
plugin_path = os.path.dirname(plugin_filepath)

try:
  STARTUP_INFO = subprocess.STARTUPINFO()
  STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
  STARTUP_INFO.wShowWindow = subprocess.SW_HIDE
except (AttributeError):
    STARTUP_INFO = None
    
_haxe_ = None

# based on https://github.com/snowkit/sublime_haxe and https://github.com/snowkit/sublime_flow by Sven Bergström


class HaxeProject(sublime_plugin.EventListener):

    def __init__(self):

        global _haxe_
        _haxe_ = self

        self.hxml_file = ""
        self.hxml_data = None
        self.hxml_args = None

        print("[haxe] __init__")

    def set_hxml_file(self, file_name):

        if not file_name:
            print("[haxe] can't set hxml file" + str(file_name))
            return

        file_name = str(file_name)
        print("[haxe] set hxml file to " + file_name)
        sublime.status_message("set hxml file to " + file_name)

        self.hxml_file = file_name
        self.refresh_info()

    def refresh_info(self):

        print("[haxe] refresh hxml on " + self.hxml_file)

        with open(self.hxml_file, 'r') as data:
            self.hxml_data = data.read()

        self.hxml_args = self.parse_hxml(self.hxml_data)

    def parse_hxml(self, data):

        lines = data.splitlines()
        _list = []

        for l in lines:
            s = l.strip()
            if s == "" or s.startswith("#"):
                pass
            else:
                _list.append(s)
                        
        return _list

    def on_query_completions(self, view, prefix, locations):

        # print("[haxe] on_query_completions ")
        scope = view.scope_name(locations[0])

        is_haxe = 'source.haxe' in scope
        is_hxml = 'source.hxml' in scope

        if not is_haxe and not is_hxml:
            return

        offset = locations[0] - len(prefix)
        comps = None

        if is_haxe:
            comps = self.get_haxe_completions(view , offset)
        elif is_hxml:
            comps = None

        if comps is None:
            # print('[haxe] completion res was none')
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        elif(len(comps)):
            return (comps, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

        return

    def get_haxe_completions(self, view, offset):

        # print("[haxe] completion ")
        if self.hxml_file == "" or self.hxml_file is None:
            sublime.status_message("No hxml file, right click in a hxml file! {}".format(str(self.hxml_file)))
            print('[haxe] completion return [], no hxml file')
            return []

        if not self.hxml_data:
            sublime.status_message("no info/hxml, caching...")
            self.refresh_info()

        #ignore strings, comments, #if conditionals, for some reason the triggers won't work
        ifsel = view.sel()[0]
        ifsel.a -= 2; ifsel.b -= 2
        scsel = view.sel()[0]

        ifdef_score = view.score_selector(ifsel.begin(), "source - (keyword.control.directive.conditional.haxe, punctuation.definition.tag)") 
        scope_score = view.score_selector(scsel.begin(), "source - (comment, string.quoted, keyword.control.directive.conditional.haxe)") 
        # print('[haxe] ifdef score `{}`'.format(str(ifdef_score)))
        # print('[haxe] scope score `{}`'.format(str(scope_score)))

        if scope_score <= 0 or ifdef_score <= 0:
            print('[haxe] ignore invalid scope for completion')
            return None

        sel = view.sel()[0]; sel.a -= 1
        ch = view.substr(sel)

        if ch != "." and ch != "(":
            # print('[haxe] ignore completion by non . or (')
            return []

        mode = ""

        if ch == ".":
            sel.a -=1;
            sel.b -=1;
            ch = view.substr(sel)
            # ignore multiple dots case
            if ch == ".":
                print('[haxe] ignore completion')
                return []
        elif ch == "(":
            mode = "@type"
        else:
            return []

        if ch == "(":
            mode = "@type"
            offset = offset-2

        cwd = self.get_working_dir()
        filename = view.file_name()

        from .haxe_completion import _haxe_completion_
        settings = sublime.load_settings('haxe_completion.sublime-settings')
        stdio_completion = True
        if settings.has("stdio_completion") is True:
            stdio_completion = settings.get("stdio_completion")
            print("[haxe] load custom stdio_completion as {}".format(stdio_completion))

        completion_start_time = time.time()
        if stdio_completion:
            filedata = view.substr(sublime.Region(0, view.size()))
            result = _haxe_completion_.complete_stdin(cwd, filename, filedata, offset, mode, self.hxml_args)
        else:
            self.save_file_for_completion(view, filename)
            result = _haxe_completion_.complete(cwd, filename, offset, mode, self.hxml_args)
            self.restore_file_post_completion(filename)

        time_diff = time.time() - completion_start_time
        print("[haxe] completion took {}".format(time_diff))
        # print("[haxe]\n{}".format(result))

        if not result:
            return None

        err = haxe_has_error(result)
        if err:
            return self.show_errors(view, err)

        args = haxe_has_args(result)
        if args:
            return self.show_args(view, args)

        # _top = haxe_has_toplevel(result)
        # if _top:
        #     return self.show_args(view, _top)

        return haxe_completion_list(result)

    def show_errors(self, view, errs):
        
        if not errs:
            return None

        _pre = '<div class="invalid">&nbsp;Haxe Errors&nbsp;</div>'
        _css = 'div { margin:0.3em; } .flow-error-line { margin-left:1em; margin-right:2em; }'
        _res = ''
        for _err in errs:
            _res += '<div class="flow-error-line">'+_err+'</div>'

        mdpopups.show_popup(view, _pre + _res, css=_css, max_width=1280)

    def show_args(self, view, args):
        if not args:
            return []
        # print('[haxe] args ' + str(args))

        _res = []
        for _arg in args:
            if _arg == "Void":
                break
            aidx = _arg.find(':')
            if aidx != -1:
                a = _arg[:aidx]
                t = _arg[aidx+1:]
                _res.append('<span class="entity name">' + a + '</span>:<span class="storage type">' + t + '</span>')
            else:
                _res.append('<span class="storage type">' + _arg + '</span>')
        args = '<div>'+', '.join(_res)+'</div>'
        _css = 'p,div { margin:0.3em; }'
        mdpopups.show_popup(view, args, css=_css, max_width=1280)

        return None

    def save_file_for_completion( self, view, fname ):

        folder = os.path.dirname(fname)
        filename = os.path.basename( fname )
        temp_file = os.path.join( folder , "." + filename + ".tmp" )

        if os.path.exists( fname ):
            shutil.copy2( fname , temp_file )

        code = view.substr(sublime.Region(0, view.size()))
        f = codecs.open( fname , "wb" , "utf-8" , "ignore" )
        f.write( code )
        f.close()

        print("[haxe] saved file for completion")

    def restore_file_post_completion( self, fname ):

        print("[haxe] restore file post completion")

        folder = os.path.dirname( fname )
        filename = os.path.basename( fname )
        temp_file = os.path.join( folder , "." + filename + ".tmp" )

        if os.path.exists( temp_file ) :
            # print("do restore!")
            shutil.copy2( temp_file , fname )
            os.remove( temp_file )
        # else:
            # os.remove( fname )

    def get_working_dir(self):
        cwd = os.path.dirname(self.hxml_file)
        cwd = os.path.normpath( cwd )

        return cwd


# http://stackoverflow.com/a/10863489/2503795
class ChainedActionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, actions, args):
        for i, action in enumerate(actions):
            self.view.run_command(action, args[i])

def force_reload():
    modules_to_load = [
        'haxe_sublime.haxe',
        'haxe_sublime.haxe_set_hxml',
        'haxe_sublime.haxe_parse_completion_list'
        'haxe_sublime.haxe_build'
    ]

    import imp
    for mod in modules_to_load:
        if sys.modules.get(mod,None) != None:
            try:
                print("reload " + mod)
                imp.reload(sys.modules[mod])
            except:
                pass

    #only use this when developing
# force_reload()

from .haxe_set_hxml import HaxeSetHxml
from .haxe_build import HaxeBuild

