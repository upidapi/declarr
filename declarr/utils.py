import json
from typing import Callable
import jsonpath_ng.ext as jsonpath


type AccessOverload = Callable[[dict], bool] | str


def access_overload(l: dict, key: AccessOverload):
    if isinstance(key, str):
        return l[key]
    return key(l)


def to_dict(l: list, key: AccessOverload):
    res = {}
    for x in l:
        res[access_overload(x, key)] = x
    return res


def del_keys(d: dict, keys: list):
    for k in keys:
        d.pop(k, None)

    return d


def cat_req(path, existing, cfg):
    delete = {}
    update = {}
    create = {}
    for name, data in existing.items():
        if name not in cfg.keys():  # and not only_update:
            delete[name] = (f"{path}/{data['id']}", existing)

    for name, data in cfg.items():
        if name in existing.keys():
            update[name] = (f"{path}/{existing[name]['id']}", data)
            # self.put(f"{path}/{existing[name]['id']}", data)
        else:
            create[name] = (path, data)
            # self.post(path, data)
    return delete, update, create


def unique(l: list):
    return list(set(l))


def map_values(obj: dict, *f):
    def func(fs, k, v):
        if not fs:
            return v
        return func(fs[1:], k, fs[0](k, v))

    return {k: func(f, k, v) for k, v in obj.items()}


def trace(obj):
    pp(obj)
    return obj


def read_file(path: str):
    with open(path) as f:
        return f.read()


def deep_merge(*args):
    source, dest, *rem = args
    res = dict(dest)
    for k, v in source.items():
        if k in res and type(source[k]) is type(dest[k]) is dict:
            res[k] = deep_merge(source[k], dest[k])
        else:
            res[k] = source[k]

    if rem:
        return deep_merge(res, *rem)
    return res


def add_defaults(obj, ref):
    assert type(obj) is type(ref)

    if isinstance(obj, dict):
        for key in ref:
            if key not in obj:
                obj[key] = ref[key]
            else:
                add_defaults(obj[key], ref[key])

    if isinstance(obj, list) and ref:
        for i in range(len(obj)):
            add_defaults(obj[i], ref[0])

    return obj


def prettify(thing):
    if isinstance(thing, str):
        try:
            thing = json.loads(thing)
        except json.JSONDecodeError:
            pass

    try:
        return json.dumps(thing, indent=2)
    except json.JSONDecodeError:
        return str(thing)


def pp(obj):
    print(prettify(obj))


def resolve_paths(obj, paths):
    # print(paths)
    def func(_, data, field):
        # print(field)
        file_path = data[field]

        return read_file(file_path).strip()

    for path in paths:
        # print([x.value for x in  jsonpath.parse(path).find(obj)])
        jsonpath.parse(path).update(obj, func)

    return obj
