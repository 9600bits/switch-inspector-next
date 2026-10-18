import sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent))
from assets import expand_cidr, AssetError, normalize, AssetStore, write_template, import_xlsx

def run():
 assert expand_cidr("192.168.1.0/30")==["192.168.1.1","192.168.1.2"]
 assert expand_cidr("192.168.1.2/31")==["192.168.1.2","192.168.1.3"]
 assert expand_cidr("192.168.1.5/32")==["192.168.1.5"]
 try: expand_cidr("10.0.0.0/8")
 except AssetError: pass
 else: raise AssertionError("large network should be rejected")
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/"template.xlsx"; write_template(p); assert len(import_xlsx(p))==1
  s=AssetStore(Path(d)/"assets.json"); s.assets=[normalize({"host":"192.0.2.1","vendor":"H3C","username":"u","password":"p"})]; s.save()
  assert AssetStore(Path(d)/"assets.json").assets[0]["vendor"]=="hp_comware"
  assert normalize({"host":"192.0.2.2","username":"u","password":"p"})["vendor"]==""
 print("asset tests passed")
if __name__=="__main__":run()
