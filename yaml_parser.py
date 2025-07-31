import re
from pathlib import Path

re_ignore = re.compile(r"(%YAML|%TAG|---).+")
re_depth = re.compile(r"([\s-]*)?.+")
re_dict = re.compile(r"{(.+?)}")

class YAML:
    """
    yaml = YAML(name='YAML', contents=contents)
    data = yaml.to_dict()
    """
    def __init__(self, parent=None, name='', value=None, prefix='', depth=0, contents=''):
        self._parent = parent
        self._depth = depth
        self._name = name
        self._value = value
        self._children = {}
        self._prefix = prefix

        if contents:
            lines = contents.split('\n')
            self.build_dict(lines=lines, num_lines=len(lines))

    @staticmethod
    def load_yaml(filepath: Path):
        if filepath.exists():

            for encoding in ['utf-8', 'cp949', 'utf-16']:
                try:
                    return YAML(name='YAML', contents=filepath.read_text(encoding=encoding)).to_dict()
                except:
                    pass
        return {}

    def add_child(self, child):
        child._parent = self
        self._children[child._name] = child
        return child

    def build_dict(self, lines=[], num_lines=0):
        while lines:
            line = lines.pop(0)
            tokens = line.split(':', 1)
            if line and not re_ignore.match(line) and len(tokens) == 2:
                prefix = re_depth.findall(line)[0]
                num_depth = int(len(prefix) / 2) + 1
                name = tokens[0][len(prefix):].strip()
                value = tokens[1].strip()
                if name.startswith('{'):
                    # no-named dict
                    value = line[len(prefix):].strip()
                    name = ''

                is_new_list_item = '-' in prefix
                is_list_value = is_new_list_item or type(self._value) is list
                if is_list_value:
                    if self._value is None:
                        self._value = []
                    if is_new_list_item and name:
                        # list of dict
                        self._value.append({})

                is_child_value = (value and num_depth == (self._depth + 1)) or (is_list_value and num_depth == (self._depth + 2))
                if is_child_value:
                    dict_values = re_dict.match(value)
                    if dict_values:
                        value = {}
                        for dict_value in dict_values.groups()[0].split(','):
                            dict_value = dict_value.split(':', 1)
                            value[dict_value[0].strip()] = dict_value[1].strip()
                    child = YAML(name=name, value=value, prefix=prefix, depth=num_depth)
                    if is_list_value:
                        if 0 < len(self._value) and type(self._value[-1]) is dict:
                            # list of dict
                            self._value[-1][name] = child
                        else:
                            # list
                            self._value.append(child)
                    else:
                        self.add_child(child)
                else:
                    if self._depth < num_depth:
                        child = YAML(name=name, prefix=prefix, depth=num_depth)
                        self.add_child(child)
                        child.build_dict(lines=lines, num_lines=num_lines)
                    else:
                        lines.insert(0, line)
                        return

    def to_dict(self):
        contents = {}
        for child in self._children.values():
            if type(child._value) is list:
                contents[child._name] = []
                for grand_children in child._value:
                    if type(grand_children) is dict:
                        # list of dict
                        grand_child_values = {}
                        contents[child._name].append(grand_child_values)
                        for key, grand_child in grand_children.items():
                            grand_child_values[key] = grand_child._value
                    else:
                        # list
                        contents[child._name].append(grand_children._value)
            elif child._value:
                contents[child._name] = child._value
            else:
                contents[child._name] = child.to_dict()
        return contents