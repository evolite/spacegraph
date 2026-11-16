from pathlib import Path

import spacegraph as sg

SCENE = sg.load(Path(__file__).parents[1] / "examples" / "bedroom.json")


def shot_view(name):
    shot = SCENE.shots[name]
    space = SCENE.space(shot["space"], shot.get("hide", ()))
    return sg.view(space, sg.camera_for(space, shot), shot.get("subject"))


def objs(v):
    return {o["id"]: o for o in v["objects"]}


def test_facing_the_bed_from_its_foot():
    v = shot_view("foot_of_bed")
    o = objs(v)
    assert v["bounds"]["centre"]["side"] == "N" and v["bounds"]["centre"]["kind"] == "wall"
    assert o["nightstand"]["h"] == "left" and o["nightstand"]["in_frame"] > 0.7
    assert o["door"]["where"] == "behind the camera"
    assert o["print"]["behind_subject"]


def test_subject_sides():
    s = shot_view("foot_of_bed")["subject"]
    assert s["view"] == "back" and s["her_right_side"] == "frame-right"
    s = shot_view("doorway_wide")["subject"]
    assert s["view"] == "front" and s["her_right_side"] == "frame-left"


def test_mirror_shows_her_front_with_matching_sides():
    m = shot_view("mirror_from_behind")["mirrors"][0]
    assert m["subject"]["view"] == "front"
    assert m["subject"]["reflected_her_right_side"] == "frame-right"
    assert "rail" in {o["id"] for o in m["shows"]}


def test_hide_and_on_children():
    space = SCENE.space("bedroom", {"bottle"})
    assert "bottle" not in space.objects
    assert space.objects["nightstand"].children == ["lamp"]
    assert space.objects["lamp"].z0 == space.objects["nightstand"].z1


def test_map_and_draft_render():
    shot = SCENE.shots["foot_of_bed"]
    space = SCENE.space("bedroom")
    v = sg.view(space, sg.camera_for(space, shot), shot["subject"])
    assert "C" in sg.topmap(space, sg.camera_for(space, shot), v["subject"])
    assert "nightstand" in sg.draft(v, space.ground, space.sky)


def test_outdoor_open_sides():
    scene = sg.load(Path(__file__).parents[1] / "examples" / "beach.json")
    shot = scene.shots["towel_seaward"]
    space = scene.space(shot["space"])
    v = sg.view(space, sg.camera_for(space, shot), shot["subject"])
    assert v["bounds"]["centre"] == {"side": "E", "kind": "open", "desc": space.open["E"]}
    o = {x["id"]: x for x in v["objects"]}
    assert o["boat"]["depth"] == "background" and o["tower"]["where"] == "behind the camera"
    assert "In the distance, the sea" in sg.draft(v, space.ground, space.sky)
