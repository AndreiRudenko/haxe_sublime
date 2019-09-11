
import sublime, sublime_plugin
import xml.etree.ElementTree as ET

print("[haxe_parse_completion_list] init")

def haxe_has_error(_input):

    if not _input:
        return False
        
    if _input[0] != '<':
        _res = []
        for _line in _input.splitlines():
            _res.append(sanitize(_line.strip()))
        
        return _res

    return False

def haxe_has_toplevel(_list):

    root = ET.fromstring(str(_list))
    if root.tag == 'il':
        return parse_toplevel(root.text.strip())

    return None

def haxe_has_args(_list):
    root = ET.fromstring(str(_list))
    # print(str(root.tag))
    
    if root.tag == 'type':
        return parse_type(root.text.strip())

    return None

def haxe_completion_list(_list):

    if _list is None:
        return None
    
    root = ET.fromstring(str(_list))

        #list is completion of properties/methods on an object/Type
    if root.tag == 'list':

        members = []

        for node in root:

            _name = node.attrib['n']
            _type = node.find('t').text

            if _type is None:
                if _name[0].islower():
                    _type = "package"
                else:
                    _type = "module" #TODO: check this case
                    # _type = _name

            _type = _type.replace(" : ", ":")

            members.append( (_name+'\t'+_type, _name) )


        if len(members):
            return members
        else:
            return [('No members/properties', '')]

    return None

#returns args, return_type from a <type> string

def parse_args(type):

    tmp = type
    args = []
    count = 0
    result = 0
    oldstyle = type[0] != "("

    if oldstyle:
        # print("oldstyle")
        while result != None:
            arg = None
            result = tmp.find(' -> ')

            if result != -1:
                arg = tmp[:result]

            if arg:
                args.append(arg)
                tmp = tmp[result+4:]

            count +=1
            if count > 10 or result == -1:
                result = None
    else:
        # print("newstyle")
        tmp = tmp[1:].replace(" : ", ":")

        while result != None:
            arg = None
            result = tmp.find(',')

            if result != -1:
                arg = tmp[:result]
            else:
                result = tmp.find(') ->')
                arg = tmp[:result]
                tmp = tmp[result+4:]
                result = -1

            if arg:
                args.append(arg)
                tmp = tmp[result+2:]

            count +=1
            if count > 10 or result == -1:
                result = None

    return args, tmp


#returns a single tuple parsed for legibility as function args, clamped if too long etc
def parse_type(_type):

    print("[haxe] parse type " + str(_type))

    if _type is None:
        return None

    if _type == "":
        return []

    _list = []

    _args, _return = parse_args(_type)
    print("_args: " + str(_args))

    for a in _args:
        _list.append(sanitize(a))

    return _list

def parse_toplevel(_type):
    return ""

def sanitize(_str):
    _str = _str.replace('>','&gt;')
    _str = _str.replace('<','&lt;')
    return _str


#returns True if the string is completion info for a function
def is_function(_str):
    if _str and len(_str):
        return _str[0] == "(" or _str.find("->") != -1
    else:
        return False
