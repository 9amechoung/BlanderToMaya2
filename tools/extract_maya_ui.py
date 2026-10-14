# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract Maya's main-menu structure from a local Maya installation.

Reads the menu-building MEL scripts and the English string table of the
Maya install on *this* machine and writes build/maya_menus.json:

    {"Modeling": {"Mesh": [item, ...], ...}, "Common": {...}, ...}

Each item is {"kind": "item"|"divider"|"submenu", "label", "rtc",
"option_box", "items"}. Only names and ordering are recorded; no MEL code.

Usage:
    python -I tools/extract_maya_ui.py ["C:/Program Files/Autodesk/Maya2025"]
"""

import json
import os
import re
import sys

MAYA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files\Autodesk\Maya2025"
STARTUP = os.path.join(MAYA, "scripts", "startup")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "maya_menus.json")

# Maya main menus per menu set -> the startup script that builds them.
MENUS = {
    "Common": {
        "File": "FileMenu", "Edit": "buildEditMenu", "Create": "ModCreateMenu",
        "Select": "buildSelectMenu", "Modify": "ModObjectsMenu", "Display": "buildDisplayMenu",
        "Windows": "WindowMenu",
    },
    "Modeling": {
        "Mesh": "PolygonsMeshMenu", "Edit Mesh": "PolygonsBuildMenu",
        "Mesh Tools": "PolygonsBuildToolsMenu", "Mesh Display": "ModelingMeshDisplayMenu",
        "Curves": "ModelingCurvesMenu", "Surfaces": "ModelingSurfacesMenu",
        "Deform": "ChaDeformationsMenu", "UV": "ModelingUVMenu",
    },
    "Rigging": {
        "Skeleton": "ChaSkeletonsMenu", "Skin": "ChaSkinningMenu", "Deform": "ChaDeformationsMenu",
        "Constrain": "AniConstraintsMenu", "Control": "ChaControlsMenu",
    },
    "Animation": {
        "Key": "AniKeyMenu", "Playback": "AniPlaybackMenu", "Visualize": "AniVisualizeMenu",
        "Deform": "ChaDeformationsMenu", "Constrain": "AniConstraintsMenu",
    },
    "FX": {
        "nParticles": "DynParticlesMenu", "Fluids": "DynFluidsMenu", "nCloth": "DynClothMenu",
        "nHair": "DynCreateHairMenu", "Fields/Solvers": "DynFieldsSolverMenu",
        "Effects": "DynEffectsMenu", "nCache": "NucleusCacheMenu",
    },
}


def load_strings():
    strings = {}
    pattern = re.compile(r'^(\S+)\s*=\s*"(.*)"\s*$')
    with open(os.path.join(MAYA, "resources", "MayaStrings"), encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                strings[m.group(1)] = m.group(2)
    return strings


def strip_comments(src):
    out, i, n, in_str = [], 0, len(src), False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
            continue
        elif src.startswith("/*", i):
            end = src.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def statements(src):
    buf, in_str = [], False
    for i, c in enumerate(src):
        if in_str:
            buf.append(c)
            if c == '"' and src[i - 1] != "\\":
                in_str = False
            continue
        if c == '"':
            in_str = True
        if c in ";{}":
            text = "".join(buf).strip()
            if text:
                yield " ".join(text.split())
            buf = []
            continue
        buf.append(c)


def runtime_labels(strings):
    """runTimeCommand name -> English label."""
    src = strip_comments(open(os.path.join(STARTUP, "defaultRunTimeCommands.mel"),
                              encoding="latin-1").read())
    labels = {}
    for st in statements(src):
        if not st.startswith("runTimeCommand"):
            continue
        name = st.split()[-1]
        key = re.search(r'-label\s*\(uiRes\("([^"]+)"\)\)', st)
        if key and key.group(1) in strings:
            labels[name] = strings[key.group(1)]
    return labels


def camel_to_words(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).strip()


def parse_menu(script, strings, rtc_labels):
    path = os.path.join(STARTUP, script + ".mel")
    src = strip_comments(open(path, encoding="latin-1").read())
    root = []
    stack = [root]
    last_item = None
    variables = {}
    for st in statements(src):
        assign = re.match(r'(?:string\s+)?\$(\w+)\s*=\s*"([^"]*)"$', st)
        if assign:
            variables[assign.group(1)] = assign.group(2)
            continue
        st = re.sub(r"\$(\w+)", lambda m: '"%s"' % variables[m.group(1)]
                    if m.group(1) in variables else m.group(0), st)
        if re.match(r"setParent\s+(-m|-menu)\s+\.\.", st):
            if len(stack) > 1:
                stack.pop()
            continue
        if re.match(r"setParent\s+(-m|-menu)\s+\$", st):
            del stack[1:]
            continue
        if not st.startswith("menuItem"):
            continue
        # `runTimeCommand -q -l X` in backticks names the command; drop the
        # backtick text so its -q flag isn't mistaken for a menu query.
        queried = re.search(r'`runTimeCommand\s+-q(?:uery)?\s+-l(?:abel)?\s+"?(\w+)"?\s*`', st)
        st = re.sub(r"`[^`]*`", "``", st)
        if re.search(r"\s-(e|edit|ex|exists|q|query)\b", st):
            continue
        if re.search(r"-(ob|optionBox)\s+(1|true)", st):
            if last_item is not None:
                last_item["option_box"] = True
            continue
        if re.search(r"-(d|divider)\s+(1|true)", st):
            key = re.search(r'-dividerLabel\s*\(uiRes\("([^"]+)"\)\)', st)
            stack[-1].append({"kind": "divider",
                              "label": strings.get(key.group(1), "") if key else ""})
            continue
        rtc_name = ""
        rtc = re.search(r'-(rtc|runTimeCommand)\s+"?(\w+)"?', st)
        command = re.search(r'-(c|command)\s+\(?\s*"(\w+)"\s*\)?(\s|$)', st)
        if rtc:
            rtc_name = rtc.group(2)
        elif queried:
            rtc_name = queried.group(1)
        elif command and command.group(2) in rtc_labels:
            rtc_name = command.group(2)
        key = re.search(r'-(l|label)\s*\(?\s*uiRes\("([^"]+)"\)', st)
        literal = re.search(r'-(l|label)\s+"([^"]+)"', st)
        label = ""
        if key:
            label = strings.get(key.group(2), "")
        elif literal:
            label = literal.group(2)
        elif rtc_name:
            label = rtc_labels.get(rtc_name) or camel_to_words(rtc_name)
        if not label and not rtc_name:
            continue
        item = {"kind": "item", "label": label, "rtc": rtc_name}
        if re.search(r"-(sm|subMenu)\s+(1|true)", st):
            item["kind"] = "submenu"
            item["items"] = []
            stack[-1].append(item)
            stack.append(item["items"])
            last_item = None
            continue
        stack[-1].append(item)
        last_item = item
    return root


def main():
    strings = load_strings()
    rtc_labels = runtime_labels(strings)
    result = {}
    for menu_set, menus in MENUS.items():
        result[menu_set] = {}
        for title, script in menus.items():
            result[menu_set][title] = parse_menu(script, strings, rtc_labels)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)

    def count(items):
        return sum(1 + count(i.get("items", [])) for i in items if i["kind"] != "divider")
    for menu_set, menus in result.items():
        print(menu_set, {t: count(i) for t, i in menus.items()})
    print("wrote", os.path.normpath(OUT))
    write_menu_data(result)


def _compact(items):
    """JSON items -> nested tuples used by the add-on:
    ("-", label) divider, ("i", label, rtc, option_box), ("s", label, [items])."""
    out = []
    for it in items:
        if it["kind"] == "divider":
            if out and out[-1][0] == "-":
                out.pop()  # collapse consecutive dividers
            out.append(("-", it["label"]))
        elif it["kind"] == "submenu":
            children = _compact(it["items"])
            if any(c[0] != "-" for c in children):
                out.append(("s", it["label"], children))
        elif it["label"]:
            out.append(("i", it["label"], it["rtc"], bool(it.get("option_box"))))
    while out and out[-1][0] == "-":
        out.pop()
    while out and out[0][0] == "-" and not out[0][1]:
        out.pop(0)
    return out


def write_menu_data(result):
    import pprint
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "addon", "maya_mode", "menu_data.py")
    data = {menu_set: [(title, _compact(items)) for title, items in menus.items()]
            for menu_set, menus in result.items()}
    with open(path, "w", encoding="utf-8") as f:
        f.write("# SPDX-License-Identifier: GPL-3.0-or-later\n")
        f.write('"""Maya main-menu layout (menu names and order only).\n\n'
                "Generated by tools/extract_maya_ui.py - do not edit by hand.\n"
                'Item tuples: ("-", label) divider, ("i", label, command, has_option_box),\n'
                '("s", label, [items]) submenu."""\n\n')
        f.write("MENU_SETS = ")
        f.write(pprint.pformat(data, width=100, sort_dicts=False))
        f.write("\n")
    print("wrote", os.path.normpath(path))


if __name__ == "__main__":
    main()
