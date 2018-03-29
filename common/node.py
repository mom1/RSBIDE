# -*- coding: utf-8 -*-
# @Author: Maximus
# @Date:   2018-03-29 11:01:13
# @Last Modified by:   Maximus
# @Last Modified time: 2018-03-29 13:11:15


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
