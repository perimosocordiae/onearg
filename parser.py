import pyparsing as pp


def _setup():
  LPAREN = pp.Literal('(').suppress()
  RPAREN = pp.Literal(')').suppress()
  COMMA = pp.Literal(',').suppress()

  # strings and integer literals only, for now
  literal = pp.Or([
      pp.quotedString,
      pp.Word(pp.nums, pp.nums + '.'),
  ]).setResultsName('literal')

  # basic alphanumeric/underscore identifiers
  identifier = pp.Word(pp.alphas + '_', pp.alphanums + '_').setResultsName('id')

  # type name is plain or parameterized: thunk[T], array[T], etc.
  type_name = pp.Forward()
  param_type = pp.Group(pp.And([
    identifier,
    pp.Literal('[').suppress(),
    type_name,
    pp.Literal(']').suppress()
  ])).setResultsName('param_type')
  type_name << pp.Group(param_type | identifier).setResultsName('type_name')

  # type declarations look like "name: type"
  type_def = pp.Group(identifier + pp.Literal(':').suppress() + type_name)
  # struct types look like "(name1: type1, name2: type2, ...)"
  struct_def = pp.Group(pp.And([
      LPAREN,
      pp.ZeroOrMore(type_def + COMMA),
      pp.Optional(type_def),
      RPAREN,
  ])).setResultsName('struct_def')

  # expressions can nest
  expression = pp.Forward()

  # return statements are a special case, similar to a function call.
  ret_expr = pp.Group(pp.Literal('return').suppress() + expression
                      ).setResultsName('return')

  # function calls are simple juxtaposition: "func arg"
  # note that evaluating an expression as a function is not allowed
  call_expr = pp.Group(identifier + expression).setResultsName('call_expr')

  # assignment is an expression: "lvalue = rvalue"
  assignment_expr = pp.Group(pp.And([
      identifier,
      pp.Literal('=').suppress(),
      expression,
  ])).setResultsName('assignment_expr')

  # struct creation: "(name1 = value1, name2 = value2, ...)"
  struct_expr = pp.Group(pp.And([
      LPAREN,
      pp.ZeroOrMore(assignment_expr + COMMA),
      pp.Optional(assignment_expr),
      RPAREN,
  ])).setResultsName('struct_expr')

  # scopes: "{ expr; expr; ... }"
  scope = pp.Group(pp.And([
      pp.Literal('{').suppress(),
      pp.ZeroOrMore(expression + pp.Literal(';').suppress()),
      pp.Literal('}').suppress(),
  ])).setResultsName('scope')

  # function definitions are a signature + body: "argtype -> rettype { body }"
  func_type = pp.Group(pp.And([
      pp.Group(struct_def | type_name).setResultsName('arg_type'),
      pp.Literal('->').suppress(),
      pp.Group(struct_def | type_name).setResultsName('ret_type'),
  ])).setResultsName('func_type')
  # function bodies are just scopes
  func_def = pp.Group(pp.And([
      func_type,
      scope
  ])).setResultsName('func_def')

  # note that function definitions aren't expressions, so no lambdas allowed
  expression << pp.Group(pp.Or([
      ret_expr,
      literal,
      scope,
      assignment_expr,
      struct_expr,
      call_expr,
      identifier,
  ])).setResultsName('expr')

  # structs and function declarations are defined the same way: "name := decl"
  definition = pp.Group(pp.And([
      identifier,
      pp.Literal(':=').suppress(),
      (func_def | struct_def),
  ]))

  # a program is a set of definitions
  program = pp.ZeroOrMore(definition)
  program.ignore(pp.cppStyleComment)
  return program

PARSER = _setup()

if __name__ == '__main__':
  import sys
  prog = PARSER.parseFile(sys.argv[1], parseAll=True)
  for defn in prog:
    print('LET', defn['id'], '=', defn[1])
