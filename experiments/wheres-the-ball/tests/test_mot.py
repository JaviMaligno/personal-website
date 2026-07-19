import pytest

from wheresball.dataset.mot import (
    classify_ball_state,
    parse_gameinfo,
    parse_mot,
    tracking_to_item,
)
from wheresball.schema import BallState

GAMEINFO = """\
[Sequence]
name=SNMOT-060
trackletID_1=player team left; 1
trackletID_2=player team right; 7
trackletID_3=goalkeeper team left; 13
trackletID_4=ball
trackletID_5=referee
"""

# frame,track_id,x,y,w,h,conf — 1920x1080 frame. Track 1 moves right between
# frames 1 and 6; the ball (track 4) sits at track 1's feet at frame 6.
MOT = """\
1,1,190,500,20,60,1
1,2,960,300,20,60,1
1,3,60,500,20,60,1
1,4,205,545,10,10,1
1,5,500,200,20,60,1
6,1,240,500,20,60,1
6,2,960,300,20,60,1
6,3,60,500,20,60,1
6,4,255,545,10,10,1
6,5,500,200,20,60,1
"""


def test_parse_gameinfo_labels():
    labels = parse_gameinfo(GAMEINFO)
    assert labels[4] == "ball"
    assert "player" in labels[1]
    assert "referee" in labels[5]
    assert len(labels) == 5


def test_parse_mot_records():
    records = parse_mot(MOT)
    assert len(records) == 10
    assert records[0].frame == 1 and records[0].track_id == 1
    assert records[3].center == (210.0, 550.0)
    with pytest.raises(ValueError):
        parse_mot("1,2,3\n")


def test_tracking_to_item_builds_players_ball_and_velocity():
    item = tracking_to_item(
        parse_mot(MOT),
        parse_gameinfo(GAMEINFO),
        target_frame=6,
        image_size=(1920, 1080),
        sequence_id="SNMOT-060",
        fps=25.0,
        velocity_window=5,
    )
    # Referee (track 5) excluded; players 1, 2, 3 included.
    assert len(item.players) == 3
    assert item.item_id == "SNMOT-060-f000006"
    assert item.ball == pytest.approx((260 / 1920, 550 / 1080))
    moving = next(p for p in item.players if p.player_id == "t1")
    static = next(p for p in item.players if p.player_id == "t2")
    assert moving.vx > 0.1  # 50 px over 0.2 s, normalized
    assert static.speed == pytest.approx(0.0)
    # Ball at the moving player's feet, slow relative to fast_ball → possession.
    assert item.state == BallState.POSSESSION
    assert item.possessor_id == "t1"


def test_tracking_to_item_requires_ball():
    records = [r for r in parse_mot(MOT) if r.track_id != 4]
    with pytest.raises(ValueError, match="no ball"):
        tracking_to_item(
            records, parse_gameinfo(GAMEINFO), 6, (1920, 1080), "SNMOT-060"
        )


def test_classify_ball_state_branches():
    assert classify_ball_state(0.05, 0.01, 1) == BallState.POSSESSION
    assert classify_ball_state(0.05, 0.01, 4) == BallState.CONTESTED
    assert classify_ball_state(0.5, 0.2, 0) == BallState.LONG_PASS
    assert classify_ball_state(0.1, 0.1, 1) == BallState.SHORT_PASS
