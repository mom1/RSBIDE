# coding=utf8
from RSBIDE.node import Node

(_ROOT, _DEPTH, _BREADTH) = range(3)


class Tree:

    def __init__(self):
        self.__nodes = {}

    @property
    def nodes(self):
        return self.__nodes

    def add_node(self, identifier, parent=None, type_node=None):
        node = Node(identifier, type_node)
        self[identifier] = node

        if parent is None:
            return node
        if parent not in self.__nodes:
            self[parent] = Node(parent, None)

        self[parent].add_child(identifier)
        return node

    def display(self, identifier, depth=_ROOT, view=None, pathfile="C:\myfile"):
        if view is None:
            print('non view')
            return
        children = self[identifier].children
        if depth == _ROOT:
            view.run_command('append', {'characters': "{0}".format(identifier)})
        else:
            view.run_command('append', {'characters': '\n' + "\t" * depth + "{0}".format(identifier)})
        depth += 1
        for child in children:
            self.display(child, depth, view)  # recursive call

    def traverse(self, identifier, mode=_DEPTH):
        # Python generator. Loosly based on an algorithm from
        # 'Essential LISP' by John R. Anderson, Albert T. Corbett,
        # and Brian J. Reiser, page 239-241
        yield identifier
        queue = self[identifier].children
        while queue:
            yield queue[0]
            expansion = self[queue[0]].children
            if mode == _DEPTH:
                queue = expansion + queue[1:]  # depth-first
            elif mode == _BREADTH:
                queue = queue[1:] + expansion  # width-first

    def __getitem__(self, key):
        return self.__nodes[key]

    def __setitem__(self, key, item):
        self.__nodes[key] = item
