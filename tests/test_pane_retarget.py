import json
import pathlib
import subprocess
import tempfile

root=pathlib.Path(__file__).resolve().parents[1]
source=root/"ui_mapping/original_pane_geometry.json"
with tempfile.TemporaryDirectory() as d:
    output=pathlib.Path(d)/"retarget.json"
    subprocess.run(["python3",str(root/"tools/retarget_panes.py"),str(source),str(output)],check=True)
    data=json.loads(output.read_text())
    assert len(data["layouts"])==22
    for layout in data["layouts"]:
        assert layout["target_size"]==[256,192]
        assert pathlib.Path(layout["source_path"]).name==layout["source"]
        w,h=layout["source_size"]
        assert layout["scale"]==[256/w,192/h]
        def verify(p):
            assert isinstance(p["flags"],int) and 0<=p["flags"]<=255
            assert isinstance(p["origin"],int) and 0<=p["origin"]<=255
            assert isinstance(p["alpha"],int) and 0<=p["alpha"]<=255
            assert len(p["rotation"])==3 and len(p["scale"])==2
            assert isinstance(p["translation_z"],(int,float))
            assert len(p["translation_ds"])==2
            assert len(p["size_ds"])==2
            for c in p["children"]:verify(c)
        for pane in layout["panes"]:verify(pane)
    title=next(x for x in data["layouts"] if x["source"]=="MnIf_U_Title.bclyt")
    assert title["source_size"]==[400.0,240.0]
    assert title["scale"]==[0.64,0.8]
    assert title["panes"][0]["size_ds"]==[256,192]
print("PASS: 22 original UI pane hierarchies retargeted to DS viewport")
