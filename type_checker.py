from collections import defaultdict

from parser import PARSER
from syntax_tree import build_ast
from type_objects import BuiltinType, FuncType


def check_types(syntax_tree):
  all_types = defaultdict(dict)

  # Define builtin primitive types.
  for t in ('int', 'float', 'string', 'void'):
    all_types[t][None] = BuiltinType(t)

  # Define builtin function types.
  builtin_tree = build_ast(PARSER.parseFile('builtins.oa', parseAll=True))
  register_defined_types(builtin_tree, all_types)

  # hack: add thunk versions, too.
  if_fns = all_types['if']
  for old_t in list(if_fns.values()):
    thunk_t = 'thunk[%s]' % old_t.ret.name
    new_t = FuncType(dict(arg_type=dict(struct_def=[('cond', 'int'),
                                                    ('then', thunk_t),
                                                    ('else', thunk_t)]),
                          ret_type=dict(id=old_t.ret.name)))
    if_fns[new_t.signature()] = new_t

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
