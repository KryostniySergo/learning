a = {"x": 1, "y": 2}
b = {"y": 3, "z": 4}

merge = {}
for key in (a.keys() | b.keys()):
    merge[key] = a.get(key, 0) + b.get(key, 0)

print(merge)

merge_v2 = {key: a.get(key, 0) + b.get(key, 0) for key in (a.keys() | b.keys())}

print(merge_v2)