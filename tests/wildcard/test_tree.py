from dynamicprompts.wildcards.collection.list import ListWildcardCollection
from dynamicprompts.wildcards.tree import WildcardTree, WildcardTreeNode


def test_synthetic_tree():
    # Silly test for an entirely synthetic tree...
    root = WildcardTreeNode()
    root.collections["mike"] = ListWildcardCollection(["one", "two"])
    root.collections["joe"] = ListWildcardCollection(["coffee", "regular"])
    root.child_nodes["jane"] = WildcardTreeNode("jane")
    root.child_nodes["jane"].collections["doe"] = ListWildcardCollection(["homer"])
    wt = WildcardTree(root=root)
    assert set(wt.map) == {"mike", "joe", "jane/doe"}
