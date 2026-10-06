"""
graphs.py - Graphviz renderers for the report figures:
  * DFD level 0 (context diagram)
  * DFD level 1 (processes, data stores, external entities)
  * firmware flowchart
  * system block diagram
Notation: Gane-Sarson / Yourdon hybrid that most Indian university reports use:
  external entity = rectangle, process = circle/rounded box with number,
  data store = open-ended box "D1 | name", data flow = labelled arrow.
"""
import subprocess, textwrap

FONT = "DejaVu Sans"


def _esc(s):
    return s.replace('"', '\\"')


def _wrap(s, n=18):
    return "\\n".join(textwrap.wrap(s, n)) if len(s) > n else s


def _render(dot_src, out_png, dpi=200):
    subprocess.run(["dot", "-Tpng", f"-Gdpi={dpi}", "-o", out_png], input=dot_src.encode(), check=True)


def dfd0(system_name, entities, out_png):
    """entities: list of (name, flow_in_to_system or None, flow_out_from_system or None)"""
    g = [f'digraph G {{ graph [rankdir=LR, splines=true, nodesep=0.5, ranksep=1.3, fontname="{FONT}", pad=0.3];',
         f'node [fontname="{FONT}", fontsize=11]; edge [fontname="{FONT}", fontsize=9.5, color="#334155"];',
         f'P0 [shape=circle, width=2.3, fixedsize=true, style=filled, fillcolor="#ccfbf1", color="#0f766e", penwidth=2, '
         f'label="0\\n{_esc(_wrap(system_name, 16))}"];']
    half = (len(entities) + 1) // 2
    for i, (name, fin, fout) in enumerate(entities):
        nid = f"E{i}"
        g.append(f'{nid} [shape=box, style="filled", fillcolor="#f1f5f9", color="#475569", penwidth=1.5, '
                 f'margin="0.2,0.12", label="{_esc(_wrap(name, 22))}"];')
        left = i < half
        if fin:
            if left:
                g.append(f'{nid} -> P0 [label="{_esc(_wrap(fin, 26))}"];')
            else:
                g.append(f'P0 -> {nid} [dir=back, label="{_esc(_wrap(fin, 26))}"];')
        if fout:
            if left:
                g.append(f'{nid} -> P0 [dir=back, label="{_esc(_wrap(fout, 26))}", color="#0f766e", fontcolor="#0f766e"];')
            else:
                g.append(f'P0 -> {nid} [label="{_esc(_wrap(fout, 26))}", color="#0f766e", fontcolor="#0f766e"];')
    g.append("}")
    _render("\n".join(g), out_png)


def dfd1(processes, stores, entities, flows, out_png):
    """processes: [(id, name)], stores: [(id, name)], entities: [(id, name)],
       flows: [(src_id, dst_id, label)]"""
    g = [f'digraph G {{ graph [rankdir=TB, splines=true, nodesep=0.6, ranksep=0.75, fontname="{FONT}", pad=0.3, newrank=true];',
         f'node [fontname="{FONT}", fontsize=10.5]; edge [fontname="{FONT}", fontsize=8.8, color="#334155"];']
    for pid, name in processes:
        g.append(f'"{pid}" [shape=circle, width=1.55, fixedsize=true, style=filled, fillcolor="#ccfbf1", color="#0f766e", '
                 f'penwidth=1.8, label="{pid}\\n{_esc(_wrap(name, 13))}"];')
    for sid, name in stores:
        g.append(f'"{sid}" [shape=record, style=filled, fillcolor="#fef9c3", color="#a16207", '
                 f'label="{sid} | {_esc(name)}"];')
    for eid, name in entities:
        g.append(f'"{eid}" [shape=box, style=filled, fillcolor="#f1f5f9", color="#475569", penwidth=1.4, '
                 f'margin="0.15,0.1", label="{_esc(_wrap(name, 20))}"];')
    for a, b, lab in flows:
        g.append(f'"{a}" -> "{b}" [label="{_esc(_wrap(lab, 22))}"];')
    g.append("}")
    _render("\n".join(g), out_png)


def flowchart(nodes, edges, out_png):
    """nodes: [(id, kind, text)] kind in start/end/process/decision/io
       edges: [(a, b, label)]"""
    shapes = {
        "start": 'shape=ellipse, style=filled, fillcolor="#0f766e", fontcolor="white"',
        "end": 'shape=ellipse, style=filled, fillcolor="#0f766e", fontcolor="white"',
        "process": 'shape=box, style="rounded,filled", fillcolor="#f1f5f9", color="#475569"',
        "decision": 'shape=diamond, style=filled, fillcolor="#fef9c3", color="#a16207"',
        "io": 'shape=parallelogram, style=filled, fillcolor="#e0f2fe", color="#0369a1"',
    }
    g = [f'digraph G {{ graph [rankdir=TB, splines=ortho, nodesep=0.45, ranksep=0.38, fontname="{FONT}", pad=0.3];',
         f'node [fontname="{FONT}", fontsize=10.5, margin="0.15,0.06"]; edge [fontname="{FONT}", fontsize=9, color="#334155"];']
    for nid, kind, text in nodes:
        w = 20 if kind == "decision" else 30
        g.append(f'"{nid}" [{shapes[kind]}, label="{_esc(_wrap(text, w))}"];')
    for e in edges:
        a, b = e[0], e[1]
        lab = e[2] if len(e) > 2 else ""
        extra = e[3] if len(e) > 3 else ""
        g.append(f'"{a}" -> "{b}" [xlabel="{_esc(lab)}" {extra}];')
    g.append("}")
    _render("\n".join(g), out_png)


def block(center, inputs, outputs, links, out_png):
    """inputs/outputs: [name]; links: [(name, label)] for comms (BLE app, cloud)"""
    g = [f'digraph G {{ graph [rankdir=LR, splines=true, nodesep=0.35, ranksep=0.9, fontname="{FONT}", pad=0.3];',
         f'node [fontname="{FONT}", fontsize=11, shape=box, style="rounded,filled", margin="0.2,0.1"]; '
         f'edge [fontname="{FONT}", fontsize=9.5, color="#334155"];',
         f'MCU [label="{_esc(center)}", fillcolor="#0f3d3a", fontcolor="white", width=2.2, height=1.6, fontsize=13];',
         'PWR [label="5 V USB /\\nadapter", fillcolor="#fee2e2", color="#dc2626"]; PWR -> MCU [label="power", color="#dc2626"];']
    for i, n in enumerate(inputs):
        g.append(f'I{i} [label="{_esc(_wrap(n, 22))}", fillcolor="#e0f2fe", color="#0369a1"]; I{i} -> MCU;')
    for i, n in enumerate(outputs):
        g.append(f'O{i} [label="{_esc(_wrap(n, 22))}", fillcolor="#fef3c7", color="#b45309"]; MCU -> O{i};')
    for i, (n, lab) in enumerate(links):
        g.append(f'L{i} [label="{_esc(_wrap(n, 22))}", fillcolor="#ccfbf1", color="#0f766e"]; '
                 f'MCU -> L{i} [dir=both, label="{_esc(lab)}", color="#0f766e", fontcolor="#0f766e"];')
    g.append("{rank=same; PWR;}")
    g.append("}")
    _render("\n".join(g), out_png)
