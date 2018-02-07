from collections import defaultdict
from type_objects import BuiltinType, FuncType


def check_types(syntax_tree):
  all_types = defaultdict(dict)

  # Define builtin primitive types.
  for t in ('int', 'float', 'string', 'void'):
    all_types[t][None] = BuiltinType(t)

  # hack: define the builtin `say` functions
  say_types = all_types['say']
  for t in ('int', 'float', 'string'):
    fn_type = FuncType(dict(arg_type=dict(id=t), ret_type=dict(id='void')))
    say_types[fn_type.signature()] = fn_type

  # First pass: collect all defined types.
  for defn in syntax_tree:
    overloads = all_types[defn.name]
    signature = defn.type.signature()
    if signature in overloads:
      raise NameError('Duplicate definition: %s' % defn)
    overloads[signature] = defn.type

  # Second pass: make sure all defined types are known and infer types.
  for defn in syntax_tree:
    for name, bad_type in defn.type.check_sub_types(all_types):
      # This dies on the first bad type, which isn't ideal.
      raise TypeError('Unknown type in %s: %s' % (defn.info(name), bad_type))
    defn.check_types(all_types)


if __name__ == '__main__':
  import sys
  from parser import PARSER
  from syntax_tree import build_ast
  tree = build_ast(PARSER.parseFile(sys.argv[1], parseAll=True))
  check_types(tree)
  print('Types check out!')
