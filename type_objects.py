

class TypeReference(object):
  def __init__(self, name):
    if not isinstance(name, (str, bytes)):
      raise TypeError('TypeReference needs a string, got %r' % type(name))
    self.name = name

  def check_sub_types(self, unused):
    return []

  def resolve(self, known_types):
    types = known_types[self.name]
    assert types, 'No types for name: %s' % self.name
    assert len(types) == 1, 'Too many types for name: %s' % self.name
    key, = types.keys()
    return types[key].resolve(known_types)

  def signature(self):
    return self.name

  def as_c_like(self):
    return self.name


class BuiltinType(TypeReference):
  def resolve(self, unused):
    return self

  def match(self, other):
    if not isinstance(other, BuiltinType):
      return '%s != %s' % (self.name, other.signature())
    if self.name != other.name:
      return '%s != %s' % (self.name, other.name)


class ParameterizedType(object):
  def __init__(self, parse_result):
    self.outer = parse_result['id']
    self.inner = parse_type(parse_result['type_name'])

  def as_c_like(self):
    return '%s<%s>' % (self.outer, self.inner.as_c_like())

  def signature(self):
    return '%s[%s]' % (self.outer, self.inner.signature())

  def resolve(self, known_types):
    self.inner = self.inner.resolve(known_types)
    return self

  def match(self, other):
    if not isinstance(other, ParameterizedType):
      return '%s != %s' % (self.signature(), other.signature())
    if self.outer != other.outer:
      return '%s != %s' % (self.signature(), other.signature())
    return self.inner.match(other.inner)


def parse_type(type_name):
  if 'id' in type_name:
    return TypeReference(type_name['id'])
  return ParameterizedType(type_name['param_type'])


class StructType(object):
  def __init__(self, parse_result):
    self.fields = {}
    for f in parse_result:
      name, typ = tuple(f)
      self.fields[name] = parse_type(typ)

  def as_c_like(self):
    fields = ['%s %s;' % (t.as_c_like(), n) for n,t in self.fields.items()]
    return '{ %s }' % ' '.join(fields)

  def check_sub_types(self, known_types):
    for name, typ in self.fields.items():
      if typ.name not in known_types:
        yield name, typ

  def resolve(self, known_types):
    for name in self.fields:
      self.fields[name] = self.fields[name].resolve(known_types)
    return self

  def match(self, other):
    if not isinstance(other, StructType):
      return '%s != %s (not a struct)' % (self, other)
    ours = set(self.fields)
    theirs = set(other.fields)
    missing = ', '.join('`%s`' % f for f in sorted(ours - theirs))
    extra = ', '.join('`%s`' % f for f in sorted(theirs - ours))
    if missing and extra:
      return 'missing fields %s, extra fields %s' % (missing, extra)
    if missing:
      return 'missing fields %s' % missing
    if extra:
      return 'extra fields %s' % extra
    for name in other.fields:
      if name not in self.fields:
        return 'missing field `%s`' % name
      msg = self.fields[name].match(other.fields[name])
      if msg:
        return 'mismatching field `%s`: %s' % (name, msg)

  def signature(self):
    return tuple(sorted((n, t.signature()) for n,t in self.fields.items()))


class FuncType(object):
  def __init__(self, parse_result):
    arg_type = parse_result['arg_type']
    if 'struct_def' in arg_type:
      self.arg = StructType(arg_type['struct_def'])
    else:
      self.arg = parse_type(arg_type['type_name'])

    ret_type = parse_result['ret_type']
    if 'struct_def' in ret_type:
      self.ret = StructType(ret_type['struct_def'])
    else:
      self.ret = parse_type(ret_type['type_name'])

  def check_sub_types(self, known_types):
    yield from self.arg.check_sub_types(known_types)
    yield from self.ret.check_sub_types(known_types)

  def resolve(self, known_types):
    self.arg = self.arg.resolve(known_types)
    self.ret = self.ret.resolve(known_types)
    return self

  def signature(self):
    return (self.arg.signature(), self.ret.signature())
