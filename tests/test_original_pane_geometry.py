import json, math, pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[1]
data=json.loads((root/'ui_mapping/original_pane_geometry.json').read_text())
assert len(data['layouts'])==22
pane_count=0
def visit(node):
 global pane_count
 pane_count+=1
 assert node['name'] and node['type'] in ('pan1','pic1','txt1','bnd1','prt1','wnd1')
 for k in ['translation','rotation','scale','size']:
  assert all(math.isfinite(x) for x in node[k])
 for ch in node['children']:visit(ch)
for layout in data['layouts']:
 assert layout['panes']
 for pane in layout['panes']:visit(pane)
title=next(x for x in data['layouts'] if x['file'].endswith('/MnIf_U_Title.bclyt'))
root_pane=title['panes'][0]
assert root_pane['name']=='RootPane'
assert root_pane['size']==[400.0,240.0]
with tempfile.TemporaryDirectory() as tmp:
 subprocess.run(['python3',str(root/'tools/parse_original_bclyt.py'),str(root/'ui_mapping/original_ui'),str(pathlib.Path(tmp)/'parsed.json')],check=True,capture_output=True)
 reread=json.loads((pathlib.Path(tmp)/'parsed.json').read_text())
 assert [{**l, "file": pathlib.Path(l["file"]).name} for l in reread["layouts"]] == [{**l, "file": pathlib.Path(l["file"]).name} for l in data["layouts"]]
print('PASS original bclyt geometry:',len(data['layouts']),'layouts',pane_count,'panes')
