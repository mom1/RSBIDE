# coding=utf8


class Node:
    def __init__(self, identifier, type_node):
        self.__identifier = identifier
        self.__children = []
        self.__type_node = type_node

    @property
    def identifier(self):
        return self.__identifier

    @property
    def children(self):
        return self.__children

    @property
    def type_node(self):
        return self.__type_node

    def add_child(self, identifier):
        self.__children.append(identifier)
