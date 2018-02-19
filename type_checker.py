from collections import defaultdict

from parser import PARSER
from syntax_tree import build_ast
from type_objects import BuiltinType


def check_types(syntax_tree):
  all_types = defaultdict(dict)

  # Define builtin primitive types.
  for t in ('int', 'float', 'string', 'void'):
    all_types[t][None] = BuiltinType(t)

  # Define builtin function types.
  builtin_tree = build_ast(PARSER.parseFile('builtins.oa', parseAll=True))
  register_defined_types(builtin_tree, all_types)

  # First pass: collect all user-defined types.
  register_defined_types(syntax_tree, all_types)

  # Second pass: make sure all defined types are known and infer types.
  for defn in syntax_tree:
    for name, bad_type in defn.type.check_sub_types(all_types):
      # This dies on the first bad type, which isn't ideal.
      raise TypeError('Unknown type in %s: %s' % (defn.info(name), bad_type))
    defn.check_types(all_types)

  return all_types


def register_defined_types(syntax_tree, all_types):
  for defn in syntax_tree:
    overloads = all_types[defn.name]
    signature = defn.type.signature()
    if signature in overloads:
      raise NameError('Duplicate definition: %s' % defn)
    overloads[signature] = defn.type


if __name__ == '__main__':
  import sys
  tree = build_ast(PARSER.parseFile(sys.argv[1], parseAll=True))
  check_types(tree)
  print('Types check out!')
