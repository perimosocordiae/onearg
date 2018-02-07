import ast
from type_objects import StructType, FuncType, BuiltinType


class CallExpr(object):
  def __init__(self, parse_result):
    self.func_name = parse_result['id']
    self.func_arg = expression(parse_result['expr'])
    self.type = None

  def __str__(self):
    return '%s(%s)' % (self.func_name, self.func_arg)

  def infer_types(self, scope, known_types, ret_type):
    if self.type is None:
      func_overloads = known_types[self.func_name]
      if not func_overloads:
        raise TypeError('Unknown function: %s' % self.func_name)

      passed_type = self.func_arg.infer_types(scope, known_types, ret_type)
      for func_type in func_overloads.values():
        mismatch_msg = passed_type.match(func_type.arg.resolve(known_types))
        if not mismatch_msg:
          break
      else:
        raise TypeError('No valid overload for function %s: %s' % (
                        self.func_name, mismatch_msg))
      self.type = func_type.ret.resolve(known_types)
    return self.type

  def execute(self, scope):
    arg_sig = self.func_arg.type.signature()
    ret_sig = self.type.signature()
    signature = (self.func_name, arg_sig, ret_sig)
    return scope[signature].call(scope, self.func_arg.execute(scope))


class Literal(object):
  def __init__(self, parse_result):
    # should move this logic to the grammar, but eh...
    self.value = ast.literal_eval(parse_result)
    if parse_result[0] in '"\'':
      self.type = BuiltinType('string')
    elif '.' in parse_result:
      self.type = BuiltinType('float')
    else:
      self.type = BuiltinType('int')

  def __str__(self):
    return repr(self.value)

  def infer_types(self, scope, known_types, ret_type):
    return self.type

  def execute(self, scope):
    return self.value


class AssignExpr(object):
  def __init__(self, parse_result):
    self.name = parse_result['id']
    self.value = expression(parse_result['expr'])
    self.type = None

  def __str__(self):
    return '%s = %s' % (self.name, self.value)

  def infer_types(self, scope, known_types, ret_type):
    if self.type is None:
      self.type = self.value.infer_types(scope, known_types, ret_type)
      scope[self.name] = self.value
    return self.type

  def execute(self, scope):
    val = self.value.execute(scope)
    scope[self.name] = val
    return val


class StructExpr(object):
  def __init__(self, parse_result):
    self.fields = {}
    for f in parse_result:
      assn = AssignExpr(f)
      self.fields[assn.name] = assn.value
    self.type = None

  def __str__(self):
    return '{ %s }' % ', '.join('%s: %s' % t for t in self.fields.items())

  def infer_types(self, scope, known_types, ret_type):
    if self.type is None:
      self.type = StructType([])
      for name, expr in self.fields.items():
        self.type.fields[name] = expr.infer_types(scope, known_types, ret_type)
    return self.type

  def execute(self, scope):
    return {k: v.execute(scope) for k, v in self.fields.items()}


class Reference(object):
  def __init__(self, parse_result):
    self.name = parse_result
    self.type = None

  def __str__(self):
    return self.name

  def infer_types(self, scope, known_types, ret_type):
    if self.type is None:
      if self.name not in scope:
        raise NameError('Variable `%s` is not defined.' % self.name)
      self.type = scope[self.name].infer_types(scope, known_types, ret_type)
    return self.type

  def execute(self, scope):
    return scope[self.name]


class ReturnExpr(object):
  def __init__(self, parse_result):
    self.ret_val = expression(parse_result['expr'])
    self.type = None

  def __str__(self):
    return 'return %s' % self.ret_val

  def infer_types(self, scope, known_types, ret_type):
    if self.type is None:
      passed_type = self.ret_val.infer_types(scope, known_types, ret_type)
      mismatch_msg = passed_type.match(ret_type)
      if mismatch_msg:
        import IPython
        IPython.embed()
        raise TypeError('Invalid return type: ' + mismatch_msg)
      self.type = BuiltinType('void')
    return self.type

  def execute(self, scope):
    return self.ret_val.execute(scope)


EXPRESSIONS = {
    'call_expr': CallExpr,
    'literal': Literal,
    'assignment_expr': AssignExpr,
    'struct_expr': StructExpr,
    'id': Reference,
    'return': ReturnExpr,
}


def expression(parse_result):
  expr_kind, = parse_result.keys()
  expr = parse_result[expr_kind]
  return EXPRESSIONS[expr_kind](expr)


class FuncDef(object):
  def __init__(self, name, parse_result):
    self.name = name
    self.type = FuncType(parse_result['func_type'])
    self.body = [expression(expr) for expr in parse_result['func_body']]

  def __str__(self):
    return '%s %s(%s) {\n%s}' % (
        self.type.ret, self.name, self.type.arg,
        ''.join('  %s;\n' % b for b in self.body))

  def info(self, field=None):
    if field:
      return 'function %s, field %s' % (self.name, field)
    return 'function %s' % self.name

  def check_types(self, known_types):
    self.type.resolve(known_types)
    scope = {name: typ.resolve(known_types)
             for name, typ in self.type.arg.fields.items()}
    for expr in self.body:
      expr.infer_types(scope, known_types, self.type.ret)

  def call(self, outer_scope, arg):
    scope = outer_scope.copy()
    scope.update(arg)
    for expr in self.body:
      val = expr.execute(scope)
      if isinstance(expr, ReturnExpr):
        return val
    assert self.type.ret.name == 'void', (
      'No return encountered in non-void function %s' % self.name)

  def signature(self):
    return (self.name,) + self.type.signature()


class StructDef(object):
  def __init__(self, name, parse_result):
    self.name = name
    self.type = StructType(parse_result)

  def __str__(self):
    return 'struct %s %s;' % (self.name, self.type)

  def info(self, field=None):
    return 'struct %s, field %s' % (self.name, field)

  def check_types(self, known_types):
    pass  # nothing to check here


def define(parse_result):
  name = parse_result['id']
  if 'func_def' in parse_result:
    return FuncDef(name, parse_result['func_def'])
  return StructDef(name, parse_result['struct_def'])


def build_ast(parse_result):
  return [define(d) for d in parse_result]


if __name__ == '__main__':
  import sys
  from parser import PARSER
  prog = PARSER.parseFile(sys.argv[1], parseAll=True)
  for defn in build_ast(prog):
    print(defn)
    print()
