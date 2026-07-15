
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dashboard.app import app


def collect_layout_ids(component, ids=None):
    if ids is None:
        ids = set()
    comp_id = getattr(component, "id", None)
    if comp_id:
        ids.add(comp_id)
    children = getattr(component, "children", None)
    if children is None:
        return ids
    if isinstance(children, (list, tuple)):
        for child in children:
            if hasattr(child, "children") or hasattr(child, "id"):
                collect_layout_ids(child, ids)
    elif hasattr(children, "children") or hasattr(children, "id"):
        collect_layout_ids(children, ids)
    return ids


def main():
    layout_ids = collect_layout_ids(app.layout)
    print(f"Found {len(layout_ids)} component IDs in the layout.")
    problems = []
    for callback_id, callback_info in app.callback_map.items():
        for output in callback_info["output"]:
            if output.component_id not in layout_ids:
                problems.append(f"Output references '{output.component_id}' -- NOT FOUND")
        for inp in callback_info.get("inputs", []):
            if inp["id"] not in layout_ids:
                problems.append(f"Input references '{inp['id']}' -- NOT FOUND")
    if problems:
        print(f"\nFAILED -- {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("PASSED -- every callback Output/Input ID exists in the layout.")
    sys.exit(0)


if __name__ == "__main__":
    main()
