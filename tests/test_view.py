from pathlib import Path

import roomgraph as rg

SCENE = rg.load(Path(__file__).parents[1] / "examples" / "bedroom.json")


def shot_view(name):
    shot = SCENE.shots[name]
    room = SCENE.room(shot["room"], shot.get("hide", ()))
    return rg.view(room, rg.camera_for(room, shot), shot.get("subject"))


def objs(v):
    return {o["id"]: o for o in v["objects"]}


def test_facing_the_bed_from_its_foot():
    v = shot_view("foot_of_bed")
    o = objs(v)
    assert v["walls"]["centre"] == "N"
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
    room = SCENE.room("bedroom", {"bottle"})
    assert "bottle" not in room.objects
    assert room.objects["nightstand"].children == ["lamp"]
    assert room.objects["lamp"].z0 == room.objects["nightstand"].z1


def test_map_and_draft_render():
    shot = SCENE.shots["foot_of_bed"]
    room = SCENE.room("bedroom")
    v = rg.view(room, rg.camera_for(room, shot), shot["subject"])
    assert "C" in rg.topmap(room, rg.camera_for(room, shot), v["subject"])
    assert "nightstand" in rg.draft(v, room.floor, room.walls)
