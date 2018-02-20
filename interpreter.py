import operator
from type_objects import FuncType


def interpret(syntax_tree, all_types):
  # assemble the global scope
  scope = {}
  for defn in syntax_tree:
    if isinstance(defn.type, FuncType):
      scope[defn.signature()] = defn

  # hack: register the builtin functions
  say_fn = SayFunction()
  for sig in all_types['say']:
    scope[('say',) + sig] = say_fn

  if_fn = IfFunction()
  for sig in all_types['if']:
    scope[('if',) + sig] = if_fn

  for op_name in ('add', 'sub', 'mul'):
    fn = MathFunction(getattr(operator, op_name))
    for sig in all_types[op_name]:
      scope[(op_name,) + sig] = fn

  # look for the entry point: a function named `main`.
  main_sig = ('main', (), 'void')
  if main_sig not in scope:
    print('No `main` function found, stopping.')
    print(scope.keys())
    return
  scope[main_sig].call(scope, {})


class SayFunction(object):
  def call(self, scope, arg):
    print(arg)


class IfFunction(object):
  def call(self, scope, arg):
    res = arg['then'] if arg['cond'] else arg['else']
    # handle thunk case
    if hasattr(res, 'execute'):
      return res.execute(scope)
    return res


class MathFunction(object):
  def __init__(self, op):
    self.op = op

  def call(self, scope, arg):
    return self.op(arg['lhs'], arg['rhs'])


if __name__ == '__main__':
  import sys
  from parser import PARSER
  from syntax_tree import build_ast
  from type_checker import check_types

  tree = build_ast(PARSER.parseFile(sys.argv[1], parseAll=True))
  all_types = check_types(tree)
  interpret(tree, all_types)
