import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent))
from secure_collector import inspect, COMMANDS, PAGING
from devices import Device

class Fake:
    def __init__(self,prompt="SW1"): self.prompt=prompt; self.commands=[]
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def find_prompt(self): return f"<{self.prompt}>"
    def send_command(self,cmd,read_timeout=None): self.commands.append(cmd); return "read-only output"

def run():
    for vendor in COMMANDS:
        c=Fake()
        d=Device("sw","192.0.2.1",vendor,22,"u","p")
        r=inspect(d,connector=lambda **kwargs:c)
        assert r.status=="ok",r.error
        assert c.commands[0]==PAGING[vendor]
        assert c.commands[1:]==COMMANDS[vendor]
        assert all(x.startswith("display ") for x in c.commands[1:])
    c=Fake("SW1"); c.find_prompt=lambda: "[SW1]"
    r=inspect(Device("sw","192.0.2.1","huawei",22,"u","p"),connector=lambda **kwargs:c)
    assert r.status=="fail" and c.commands==[]
    print("secure collector checks passed")
if __name__=="__main__":run()
