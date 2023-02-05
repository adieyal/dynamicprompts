def cross(list1: list[str], list2: list[str], sep=",") -> list[str]:
    return [f"{x}{sep}{y}" for x in list1 for y in list2 if x != y]


def zipstr(list1: list[str], list2: list[str], sep="") -> list[str]:
    return [f"{x}{sep}{y}" for x, y in zip(list1, list2)]


def interleave(list1: list[str], list2: list[str]) -> list[str]:
    new_list = list1 + list2
    new_list[::2] = list1
    new_list[1::2] = list2

    return new_list
