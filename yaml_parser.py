import re
from pathlib import Path
import traceback

re_ignore = re.compile(r"(%YAML|%TAG|---).+")
re_depth = re.compile(r"([\s-]*)?.+")
re_dict = re.compile(r"{(.+?)}")
re_list = re.compile(r"[(.+?)]")

__logger__ = None

class YAMLGroup:
    def __init__(self):
        self._group = []

    def add_node(self, yaml_node):
        self._group.append(yaml_node)

    def get_node(self, index):
        return self._group[index]

    def get_nodes(self):
        return self._group

    def find_node(self, name):
        for yaml_node in self._group:
            if yaml_node.get_name() == name:
                return yaml_node
        return None

    def find_nodes(self, name):
        return [yaml_node for yaml_node in self._group if yaml_node.get_name() == name]

    def get_num_node(self):
        return len(self._group)


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
        self._is_yaml_group_list = False
        self._children = []
        self._prefix = prefix

        if contents:
            lines = contents.split('\n')
            self.build_yaml(lines=lines, num_lines=len(lines))

    @staticmethod
    def load_yaml(filepath: Path):
        if filepath.exists():
            for encoding in ['utf-8', 'utf-8-sig', 'cp949', 'utf-16']:
                try:
                    return YAML(name='YAML', contents=filepath.read_text(encoding=encoding))
                except:
                    __logger__.info(f'failed to load yaml file: {filepath}, encoding: {encoding}, traceback: {traceback.format_exc()}')
                    pass
        __logger__.info(f'failed to load yaml file: {filepath}')
        return None

    def get(self, key, default_value=None):
        return self._value.get(key, default_value)

    def get_prefix(self):
        return self._prefix

    def get_name(self):
        return self._name

    def get_value(self):
        return self._value

    def add_child(self, child):
        child._parent = self
        if self._is_yaml_group_list:
            self._children[-1].add_node(child)
        else:
            self._children.append(child)
        return child

    def get_child(self, name=None):
        for child in self._children:
            if name is None or child._name == name:
                return child
        return None

    def get_children(self, name=None):
        return [child for child in self._children if name is None or child._name == name]

    def build_yaml(self, lines=[], num_lines=0):
        while lines:
            line = lines.pop(0)
            tokens = line.split(':', 1)
            if line and not re_ignore.match(line):
                prefix = re_depth.findall(line)[0]
                num_depth = int(len(prefix) / 2) + 1
                if self._depth < num_depth:
                    if len(tokens) == 2:
                        name = tokens[0][len(prefix):].strip()
                        value = tokens[1].strip()
                    else:
                        name = ''
                        value = line[len(prefix):].strip()

                    # no-named dict
                    if name.startswith('{'):
                        value = line[len(prefix):].strip()
                        name = ''

                    # list of yaml group
                    if '-' in prefix:
                        if (self._depth + 1) == num_depth:
                            self._is_yaml_group_list = True
                            self._children.append(YAMLGroup())

                    # value of dict
                    list_values = re_list.match(value)
                    dict_values = re_dict.match(value)
                    if dict_values:
                        value = {}
                        for dict_value in dict_values.groups()[0].split(','):
                            dict_value = dict_value.split(':', 1)
                            value[dict_value[0].strip()] = dict_value[1].strip()
                    elif list_values:
                        value = []
                        for list_value in list_values.groups()[0].split(','):
                            value.append(list_value.strip())

                    yaml_node = YAML(name=name, value=value, prefix=prefix, depth=num_depth)
                    if (self._depth + 1) == num_depth:
                        self.add_child(yaml_node)
                    elif (self._depth + 2) == num_depth:
                        lines.insert(0, line)
                        last_child = self._children[-1]
                        if self._is_yaml_group_list:
                            last_child = last_child._group[-1]
                        last_child.build_yaml(lines=lines, num_lines=num_lines)
                    else:
                        __logger__.error(f'[{num_lines - len(lines)}] - line: {line}, depth: {self._depth}, num_depth: {num_depth}')
                else:
                    # goto parent
                    lines.insert(0, line)
                    return

    def dump(self, contents=None, depth=0):
        if depth == 0:
            contents = []

        for child in self._children:
            nodes = child.get_nodes() if isinstance(child, YAMLGroup) else [child]
            for node in nodes:
                if node.get_value():
                    contents.append(f'{node.get_prefix()}{node.get_name()}: {node.get_value()}')
                else:
                    contents.append(f'{node.get_prefix()}{node.get_name()}:')
                node.dump(contents=contents, depth=depth + 1)
        return '\n'.join(contents) if depth == 0 else None