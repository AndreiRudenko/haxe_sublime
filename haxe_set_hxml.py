import sublime, sublime_plugin

class HaxeSetHxml(sublime_plugin.WindowCommand):

    def run(self):
        from .haxe import _haxe_

        view = self.window.active_view()
        _haxe_.set_hxml_file(view.file_name())

    def is_visible(self):

        # print("[haxe] is_visible")
        view = self.window.active_view()
        pt = view.sel()[0].b
        scope = view.scope_name(pt)

        if "source.hxml" in scope:
            return True
        else:
            return False


print("[haxe] loaded set hxml file")
