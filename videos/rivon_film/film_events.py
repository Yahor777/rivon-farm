"""Pure-python export of the sound-event list (frame times) of the film timeline -> post/events.json.  usage: python3 film_events.py"""
import json, math
LAB2 = 690
def events():
    ev = []
    def add(name, a0, a1):
        ev.append(dict(name=name, f0=a0 + 4, f1=a1 + 4))                                  # assembly
        d0 = 696 + (200 - a1) / 2.2; d1 = 696 + (200 - a0) / 2.2
        ev.append(dict(name=name + "_off", f0=d0, f1=d1))                                  # disassembly (reverse, 2.2x)
    for k in range(4):
        add(f"stopa{k}", 14 + 4 * k, 42 + 4 * k); add(f"post{k}", 42 + 5 * k, 78 + 5 * k); add(f"trojak{k}", 78 + 4 * k, 104 + 4 * k)
    add("beamL", 104, 140); add("beamR", 110, 146); add("beamE1", 130, 160); add("beamE2", 136, 166)
    for i in range(11):
        add(f"mb2L{i}", 146 + i * 1.1, 146 + i * 1.1 + 17); add(f"mb2R{i}", 147.5 + i * 1.1, 147.5 + i * 1.1 + 17); add(f"rafter{i}", 152 + i * 2.0, 172 + i * 2.0)
    for i, s in enumerate((210, 306, 402, 498, 594, 690)): ev.append(dict(name="cut", f0=s - 3, f1=s))
    ev.append(dict(name="hero", f0=758, f1=798)); ev.append(dict(name="cta", f0=836, f1=870))
    return ev
if __name__ == "__main__":
    json.dump(events(), open("post/events.json", "w"))
    print(len(events()), "events")
