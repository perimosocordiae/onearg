from type_objects import FuncType


def interpret(syntax_tree):
  # assemble the global scope
  scope = {}
  for defn in syntax_tree:
    if isinstance(defn.type, FuncType):
      scope[defn.signature()] = defn

  # hack: register the builtin `say` functions
  say_fn = SayFunction()
  scope[('say', 'string', 'void')] = say_fn
  scope[('say', 'int', 'void')] = say_fn
  scope[('say', 'float', 'void')] = say_fn

  # look for the entry point: a function named `main`.
  main_sig = ('main', '()', 'void')
  if main_sig not in scope:
    print('No `main` function found, stopping.')
    print(scope.keys())
    return
  scope[main_sig].call(scope, {})


class SayFunction(object):
  def call(self, scope, arg):
    print(arg)



if __name__ == '__main__':
  import sys
  from parser import PARSER
  from syntax_tree import build_ast
  from type_checker import check_types

  tree = build_ast(PARSER.parseFile(sys.argv[1], parseAll=True))
  check_types(tree)
  interpret(tree)
