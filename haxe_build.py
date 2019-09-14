import Default

stexec = getattr( Default , "exec" )
ExecCommand = stexec.ExecCommand

class HaxeBuild(ExecCommand):

    def run(self, cmd = None, shell_cmd = None, file_regex = "", line_regex = "", working_dir = "",
            encoding = "utf-8", env = {}, quiet = False, kill = False,
            word_wrap = True, syntax = "Packages/Text/Plain text.tmLanguage",
            # Catches "path" and "shell"
            **kwargs):

        try:
            if self.proc:
                super(HaxeBuild, self).run(kill=True)
        except Exception as e:
            print("[haxe] couldn't kill previous executable: probably it ended > " + str(e))

        self.proc = None

        if kill:
            return

        from .haxe import _haxe_

        if not _haxe_.hxml_file and _haxe_.hxml_file == "":
            print("[haxe]")
            return

        working_dir = _haxe_.get_working_dir()
        cmd = [
            "haxe", _haxe_.hxml_file
        ]

        print("[haxe] build: " + " ".join(cmd))

        super(HaxeBuild, self).run( 
                cmd= None, 
                shell_cmd= " ".join(cmd),
                file_regex= file_regex, 
                line_regex= line_regex, 
                working_dir= working_dir, 
                encoding= encoding, 
                env= env, 
                quiet= False, 
                kill= kill, 
                word_wrap= word_wrap, 
                syntax= syntax, 
                **kwargs)


print("[haxe] loaded set hxml file")
