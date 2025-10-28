import importlib.metadata as im
import sys

def get_eps(group):
    try:
        return list(im.entry_points(group=group))
    except TypeError:
        all_eps = im.entry_points()
        if hasattr(all_eps, "select"):
            return list(all_eps.select(group=group))
        if isinstance(all_eps, dict):
            return list(all_eps.get(group, []))
        return []

def main():
    group = "patternanalyzer.plugins"
    eps = get_eps(group)
    print(f"found {len(eps)} entry points in group '{group}'")
    for ep in eps:
        name = getattr(ep, "name", None)
        try:
            loaded = ep.load()
            cls_name = getattr(loaded, "__name__", repr(loaded))
        except Exception as e:
            cls_name = f"load-error: {e}"
        print(f"- {name} -> {cls_name}")

if __name__ == "__main__":
    main()